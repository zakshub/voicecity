"""Tests for async generation job queue, cancellation, voice conversion endpoint, and Urdu normalization."""

from __future__ import annotations

import math
from pathlib import Path
import struct
import time
import wave

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.engine.base import (
    EngineCapability,
    GenerationCancelledError,
    GenerationRequest,
    GenerationResult,
    VerificationStatus,
    VoicePreparationResult,
)
from app.engine.registry import EngineRegistry
from app.main import create_app
from app.text.segmenter import analyze_and_segment, normalize_text
from scripts.download_models import verify_local_files


def _write_wav(path: Path, duration_sec: float = 6.0, rate: int = 24000) -> Path:
    n = int(duration_sec * rate)
    samples = [int(10000 * math.sin(2.0 * math.pi * 220.0 * i / rate)) for i in range(n)]
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack("<" + "h" * n, *samples))
    return path


class _SlowCancellableFixture:
    def __init__(self, delay_sec: float = 0.05) -> None:
        self._delay = delay_sec

    @property
    def engine_id(self) -> str:
        return "slow_fixture"

    def health_check(self) -> bool:
        return True

    def supported_languages(self) -> set[str]:
        return {"ur", "en", "mixed"}

    def capabilities(self) -> EngineCapability:
        return EngineCapability(
            engine_id=self.engine_id,
            display_name="Slow Cancellable Fixture (Test Only)",
            version="0.0.1",
            capability_class="reference_voice_cloning",
            maturity_level="experimental",
            uses_reference_audio=True,
            requires_reference_transcript=False,
            distributable_default=False,
            license_category="none",
            code_license="MIT",
            weight_license="None",
            commercial_compatible=True,
            commercial_note="Test only",
            installed=True,
            ready=True,
            offline_supported=True,
            supported_languages=["ur", "en", "mixed"],
            verified_native_languages=[],
            experimental_languages=["ur", "en", "mixed"],
            device="cpu",
            estimated_download_gb=0.0,
            min_ram_gb=1,
            min_vram_gb=None,
            cpu_feasible="Test",
            local_weights_present=True,
            status_message="Ready",
            source_url="https://github.com/zakshub/voicecity",
            license_url="https://github.com/zakshub/voicecity",
            verification=VerificationStatus(True, False, False, False, True),
        )

    def prepare_voice(
        self, voice_profile_id: str, reference_audio_path: Path, work_dir: Path
    ) -> VoicePreparationResult:
        return VoicePreparationResult(voice_profile_id, reference_audio_path, True)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        for step in (25, 50, 75):
            if request.progress_callback:
                request.progress_callback(step, f"Step {step}%")
            time.sleep(self._delay)
            if request.cancel_check and request.cancel_check():
                raise GenerationCancelledError("Cancelled cleanly")
        _write_wav(request.output_path, duration_sec=1.0)
        return GenerationResult(
            audio_path=request.output_path,
            duration_seconds=1.0,
            sample_rate_hz=24000,
            model_id="slow_fixture",
            generation_time_seconds=0.1,
            segments=[{"language": request.language, "text": request.text}],
        )


def test_enhanced_urdu_normalization_and_pronunciation_hints() -> None:
    # Urdu digits normalized, question mark harmonized, ZWNJ preserved
    raw = "کیا یہ ۲۰\u200c۲۶ کا PKR 5000 بجٹ ہے?"
    norm = normalize_text(raw)
    assert "20\u200c26" in norm
    assert norm.endswith("؟")

    analysis = analyze_and_segment("آج Rs. 500 کا API demo ہے", requested_language="ur")
    assert any("English Latin words detected" in h for h in analysis.pronunciation_hints)
    assert any("Abbreviations/acronyms" in h for h in analysis.pronunciation_hints)


def test_async_job_queue_completion_and_cancellation(tmp_path: Path) -> None:
    cfg = Settings(
        environment="test",
        data_dir=tmp_path / "data",
        model_dir=tmp_path / "models",
        tts_provider="slow_fixture",
    )
    client = TestClient(
        create_app(
            settings=cfg,
            engine_registry=EngineRegistry([_SlowCancellableFixture(delay_sec=0.06)]),
        )
    )
    wav_src = _write_wav(tmp_path / "voice.wav", duration_sec=6.0)
    vid = client.post(
        "/api/v1/voices/import",
        data={"display_name": "Queue Test", "ownership_confirmed": "true"},
        files={"file": ("voice.wav", wav_src.read_bytes(), "audio/wav")},
    ).json()["voice"]["id"]

    # 1. Enqueue and wait for completion
    enq = client.post(
        "/api/v1/jobs",
        json={"voice_profile_id": vid, "text": "Testing local queue.", "language": "en"},
    )
    assert enq.status_code == 202
    job_id = enq.json()["job"]["job_id"]

    final_job = None
    for _ in range(40):
        final_job = client.get(f"/api/v1/jobs/{job_id}").json()["job"]
        if final_job["status"] in ("completed", "failed", "cancelled"):
            break
        time.sleep(0.05)

    assert final_job is not None
    assert final_job["status"] == "completed"
    assert final_job["progress_percent"] == 100
    assert final_job["generation_id"] is not None
    assert client.get(f"/api/v1/generations/{final_job['generation_id']}").status_code == 200

    # 2. Enqueue slow job and cancel mid-flight
    enq2 = client.post(
        "/api/v1/jobs",
        json={"voice_profile_id": vid, "text": "Cancel this job.", "language": "en"},
    )
    job2_id = enq2.json()["job"]["job_id"]
    cancel_res = client.post(f"/api/v1/jobs/{job2_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["job"]["cancel_requested"] is True

    cancelled_job = None
    for _ in range(40):
        cancelled_job = client.get(f"/api/v1/jobs/{job2_id}").json()["job"]
        if cancelled_job["status"] in ("cancelled", "completed", "failed"):
            break
        time.sleep(0.05)
    assert cancelled_job is not None
    assert cancelled_job["status"] == "cancelled"


def test_voice_conversion_endpoint_honestly_reports_unavailable_and_verify_cli(tmp_path: Path) -> None:
    cfg = Settings(data_dir=tmp_path / "data", model_dir=tmp_path / "models")
    client = TestClient(create_app(settings=cfg))
    wav_src = _write_wav(tmp_path / "voice.wav", duration_sec=6.0)
    vid = client.post(
        "/api/v1/voices/import",
        data={"display_name": "Target Voice", "ownership_confirmed": "true"},
        files={"file": ("voice.wav", wav_src.read_bytes(), "audio/wav")},
    ).json()["voice"]["id"]

    conv = client.post(
        "/api/v1/conversions",
        data={"voice_profile_id": vid, "source_language": "en"},
        files={"source_file": ("src.wav", wav_src.read_bytes(), "audio/wav")},
    )
    assert conv.status_code == 503
    assert conv.json()["detail"]["error"] == "voice_converter_not_ready"

    # Offline verify returns non-zero when weights are missing
    assert verify_local_files(tmp_path / "models", "qwen3_tts_en") == 2
