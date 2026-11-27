"""Lightweight single-worker local generation queue with live progress and cancellation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import queue
import threading
from typing import Any, Callable, Literal
import uuid

from app.core.database import VoiceCityDB
from app.core.storage import LocalStorage
from app.engine.base import (
    EngineError,
    GenerationCancelledError,
    GenerationRequest,
    SpeechEngine,
)
from app.voices.models import GenerationRecord

JobStatus = Literal["queued", "running", "completed", "cancelled", "failed"]


@dataclass
class GenerationJob:
    job_id: str
    voice_profile_id: str
    voice_profile_name: str
    language: str
    engine_id: str
    text_preview: str
    status: JobStatus = "queued"
    progress_percent: int = 0
    stage_message: str = "Queued for local synthesis"
    generation_id: str | None = None
    error_message: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cancel_requested: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "voice_profile_id": self.voice_profile_id,
            "voice_profile_name": self.voice_profile_name,
            "language": self.language,
            "engine_id": self.engine_id,
            "text_preview": self.text_preview,
            "status": self.status,
            "progress_percent": self.progress_percent,
            "stage_message": self.stage_message,
            "generation_id": self.generation_id,
            "error_message": self.error_message,
            "cancel_requested": self.cancel_requested,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class _QueuedWork:
    job: GenerationJob
    engine: SpeechEngine
    request: GenerationRequest
    segments: list[dict[str, str]]
    generation_id: str
    model_fallback_name: str


class GenerationJobQueue:
    """Single-worker background thread queue keeping local CPU/GPU memory predictable."""

    def __init__(self, db: VoiceCityDB, storage: LocalStorage) -> None:
        self._db = db
        self._storage = storage
        self._lock = threading.Lock()
        self._jobs: dict[str, GenerationJob] = {}
        self._order: list[str] = []
        self._queue: queue.Queue[_QueuedWork | None] = queue.Queue()
        self._worker = threading.Thread(target=self._run_loop, name="voicecity-worker", daemon=True)
        self._worker.start()

    def enqueue(
        self,
        *,
        engine: SpeechEngine,
        request: GenerationRequest,
        voice_profile_name: str,
        segments: list[dict[str, str]],
        generation_id: str,
    ) -> GenerationJob:
        cap = engine.capabilities()
        job_id = f"job_{uuid.uuid4().hex[:10]}"
        preview = request.text[:80] + ("…" if len(request.text) > 80 else "")
        job = GenerationJob(
            job_id=job_id,
            voice_profile_id=request.voice_profile_id,
            voice_profile_name=voice_profile_name,
            language=request.language,
            engine_id=cap.engine_id,
            text_preview=preview,
        )
        with self._lock:
            self._jobs[job_id] = job
            self._order.insert(0, job_id)
            if len(self._order) > 100:
                oldest = self._order.pop()
                self._jobs.pop(oldest, None)

        self._queue.put(
            _QueuedWork(
                job=job,
                engine=engine,
                request=request,
                segments=segments,
                generation_id=generation_id,
                model_fallback_name=cap.display_name,
            )
        )
        return job

    def list_jobs(self, limit: int = 30) -> list[dict[str, Any]]:
        with self._lock:
            ids = self._order[: max(1, min(limit, 100))]
            return [self._jobs[jid].to_dict() for jid in ids if jid in self._jobs]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.to_dict() if job else None

    def cancel_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if job.status in ("completed", "failed", "cancelled"):
                return job.to_dict()
            job.cancel_requested = True
            if job.status == "queued":
                job.status = "cancelled"
                job.stage_message = "Cancelled before synthesis started"
            else:
                job.stage_message = "Cancellation requested — stopping after current step"
            job.updated_at = datetime.now(timezone.utc).isoformat()
            return job.to_dict()

    def _update_job(
        self,
        job: GenerationJob,
        *,
        status: JobStatus | None = None,
        progress: int | None = None,
        stage: str | None = None,
        generation_id: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            if status is not None:
                job.status = status
            if progress is not None:
                job.progress_percent = max(0, min(100, progress))
            if stage is not None:
                job.stage_message = stage
            if generation_id is not None:
                job.generation_id = generation_id
            if error is not None:
                job.error_message = error
            job.updated_at = datetime.now(timezone.utc).isoformat()

    def _is_cancelled(self, job: GenerationJob) -> bool:
        with self._lock:
            return job.cancel_requested

    def _run_loop(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:
                break
            job = item.job
            if self._is_cancelled(job):
                self._update_job(job, status="cancelled", stage="Cancelled before execution")
                self._queue.task_done()
                continue

            self._update_job(job, status="running", progress=5, stage="Preparing local synthesis")

            def _progress(pct: int, msg: str) -> None:
                self._update_job(job, progress=pct, stage=msg)

            def _cancel_check() -> bool:
                return self._is_cancelled(job)

            req_with_hooks = GenerationRequest(
                text=item.request.text,
                language=item.request.language,
                voice_profile_id=item.request.voice_profile_id,
                reference_audio_path=item.request.reference_audio_path,
                output_path=item.request.output_path,
                output_format=item.request.output_format,
                speed=item.request.speed,
                expression=item.request.expression,
                reference_transcript=item.request.reference_transcript,
                compute_device=item.request.compute_device,
                progress_callback=_progress,
                cancel_check=_cancel_check,
            )

            now = datetime.now(timezone.utc)
            try:
                result = item.engine.generate(req_with_hooks)
                if self._is_cancelled(job):
                    item.request.output_path.unlink(missing_ok=True)
                    self._update_job(job, status="cancelled", stage="Cancelled by user")
                else:
                    rec = GenerationRecord(
                        id=item.generation_id,
                        voice_profile_id=job.voice_profile_id,
                        voice_profile_name=job.voice_profile_name,
                        text=item.request.text,
                        language=item.request.language,
                        engine_id=job.engine_id,
                        model_id=result.model_id,
                        status="completed",
                        audio_path=str(result.audio_path),
                        duration_seconds=result.duration_seconds,
                        sample_rate_hz=result.sample_rate_hz,
                        generation_time_seconds=result.generation_time_seconds,
                        speed=item.request.speed,
                        expression=item.request.expression,
                        segments=result.segments or item.segments,
                        error_message="",
                        created_at=now,
                    )
                    self._db.create_generation(rec)
                    self._update_job(
                        job,
                        status="completed",
                        progress=100,
                        stage="Completed locally",
                        generation_id=item.generation_id,
                    )
            except GenerationCancelledError:
                item.request.output_path.unlink(missing_ok=True)
                self._update_job(job, status="cancelled", stage="Cancelled by user")
            except (EngineError, Exception) as exc:
                item.request.output_path.unlink(missing_ok=True)
                failed_rec = GenerationRecord(
                    id=item.generation_id,
                    voice_profile_id=job.voice_profile_id,
                    voice_profile_name=job.voice_profile_name,
                    text=item.request.text,
                    language=item.request.language,
                    engine_id=job.engine_id,
                    model_id=item.model_fallback_name,
                    status="failed",
                    audio_path="",
                    duration_seconds=0.0,
                    sample_rate_hz=24000,
                    generation_time_seconds=0.0,
                    speed=item.request.speed,
                    expression=item.request.expression,
                    segments=item.segments,
                    error_message=str(exc),
                    created_at=now,
                )
                self._db.create_generation(failed_rec)
                self._update_job(
                    job,
                    status="failed",
                    stage="Generation failed",
                    generation_id=item.generation_id,
                    error=str(exc),
                )
            finally:
                self._queue.task_done()
