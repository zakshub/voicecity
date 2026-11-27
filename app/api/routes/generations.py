"""Speech generation, async job queue with cancellation, voice conversion, history, and export."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse

from app.api.schemas import GenerationCreateRequest, TextAnalyzeRequest
from app.audio.service import (
    AudioExportUnavailableError,
    AudioValidationError,
    export_wav_to_mp3,
    inspect_wav,
    mp3_export_available,
)
from app.core.state import AppContext
from app.core.storage import StorageSecurityError, ensure_within_dir, sanitize_filename
from app.engine.adapters.openvoice_v2 import OpenVoiceV2ConverterEngine
from app.engine.base import (
    EngineError,
    EngineUnavailableError,
    GenerationRequest,
    UnsupportedLanguageError,
    VoiceConversionRequest,
)
from app.text.segmenter import analyze_and_segment
from app.voices.models import GenerationRecord

router = APIRouter(prefix="/api/v1", tags=["generations"])


def _ctx(request: Request) -> AppContext:
    return request.app.state.ctx  # type: ignore[no-any-return]


def _serialize_generation(rec: GenerationRecord) -> dict[str, Any]:
    has_audio = bool(rec.audio_path and Path(rec.audio_path).is_file())
    return {
        "id": rec.id,
        "voice_profile_id": rec.voice_profile_id,
        "voice_profile_name": rec.voice_profile_name,
        "text": rec.text,
        "language": rec.language,
        "engine_id": rec.engine_id,
        "model_id": rec.model_id,
        "status": rec.status,
        "duration_seconds": rec.duration_seconds,
        "sample_rate_hz": rec.sample_rate_hz,
        "generation_time_seconds": rec.generation_time_seconds,
        "speed": rec.speed,
        "expression": rec.expression,
        "segments": rec.segments,
        "error_message": rec.error_message,
        "has_audio": has_audio,
        "audio_url": f"/api/v1/generations/{rec.id}/audio?format=wav" if has_audio else None,
        "wav_download_url": (
            f"/api/v1/generations/{rec.id}/audio?format=wav&download=1" if has_audio else None
        ),
        "mp3_download_url": (
            f"/api/v1/generations/{rec.id}/audio?format=mp3&download=1"
            if (has_audio and mp3_export_available())
            else None
        ),
        "created_at": rec.created_at.isoformat(),
    }


def _validate_generation_inputs(
    ctx: AppContext, payload: GenerationCreateRequest
) -> tuple[Any, Any, Any, Any, list[dict[str, str]], GenerationRequest, str]:
    if len(payload.text) > ctx.settings.max_text_chars:
        raise HTTPException(
            status_code=400,
            detail=f"Text exceeds maximum length of {ctx.settings.max_text_chars} characters.",
        )

    profile = ctx.db.get_voice_profile(payload.voice_profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Selected voice profile was not found.")

    ref_path = Path(profile.reference_audio_path)
    if not ref_path.is_file():
        raise HTTPException(
            status_code=400,
            detail="Voice profile reference audio is missing. Re-prepare or re-import the profile.",
        )

    analysis = analyze_and_segment(payload.text, requested_language=payload.language)
    if not analysis.normalized_text:
        raise HTTPException(status_code=400, detail="Text input cannot be empty.")

    prefs = ctx.db.get_preferences(default_engine=ctx.settings.tts_provider)
    requested_engine_id = payload.engine_id or str(
        prefs.get("active_engine") or ctx.settings.tts_provider
    )
    engine = ctx.engines.resolve(requested_engine_id)
    cap = engine.capabilities()

    if cap.capability_class == "voice_conversion":
        raise HTTPException(
            status_code=400,
            detail=(
                f"'{cap.display_name}' is an audio-to-audio Voice Converter, not a Text-to-Speech "
                "engine. Use POST /api/v1/conversions or select a reference voice cloning engine."
            ),
        )

    if not cap.ready:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "engine_not_ready",
                "engine_id": cap.engine_id,
                "capability_class": cap.capability_class,
                "maturity_level": cap.maturity_level,
                "message": cap.status_message,
                "missing_requirements": cap.missing_requirements,
            },
        )

    if payload.language not in engine.supported_languages():
        raise HTTPException(
            status_code=400,
            detail=(
                f"Active engine '{cap.display_name}' does not currently support language "
                f"'{payload.language}'. Ready languages: {sorted(engine.supported_languages())}."
            ),
        )

    generation_id = f"gen_{uuid.uuid4().hex[:12]}"
    output_path = ctx.storage.generation_audio_path(profile.id, generation_id, ext="wav")
    seg_dicts = [asdict(s) for s in analysis.segments]
    gen_req = GenerationRequest(
        text=analysis.normalized_text,
        language=payload.language,
        voice_profile_id=profile.id,
        reference_audio_path=ref_path,
        output_path=output_path,
        output_format="wav",
        speed=payload.speed,
        expression=payload.expression,
        reference_transcript=profile.reference_transcript,
        compute_device=str(prefs.get("compute_device", "auto")),
    )
    return profile, engine, cap, analysis, seg_dicts, gen_req, generation_id


@router.post("/text/analyze")
def analyze_text(payload: TextAnalyzeRequest) -> dict[str, Any]:
    analysis = analyze_and_segment(payload.text, requested_language=payload.language)
    return {
        "normalized_text": analysis.normalized_text,
        "detected_language": analysis.detected_language,
        "has_urdu_script": analysis.has_urdu_script,
        "has_latin_script": analysis.has_latin_script,
        "char_count": analysis.char_count,
        "word_count": analysis.word_count,
        "segments": [asdict(s) for s in analysis.segments],
        "pronunciation_hints": analysis.pronunciation_hints,
    }


# --- Async Generation Queue with Progress & Cancellation ---


@router.post("/jobs", status_code=202)
def enqueue_generation_job(payload: GenerationCreateRequest, request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    profile, engine, _cap, _analysis, seg_dicts, gen_req, generation_id = (
        _validate_generation_inputs(ctx, payload)
    )
    job = ctx.jobs.enqueue(
        engine=engine,
        request=gen_req,
        voice_profile_name=profile.display_name,
        segments=seg_dicts,
        generation_id=generation_id,
    )
    return {"job": job.to_dict()}


@router.get("/jobs")
def list_jobs(request: Request, limit: int = Query(default=25, ge=1, le=100)) -> dict[str, Any]:
    ctx = _ctx(request)
    jobs = ctx.jobs.list_jobs(limit=limit)
    return {"jobs": jobs, "count": len(jobs)}


@router.get("/jobs/{job_id}")
def get_job(job_id: str, request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    job = ctx.jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found.")
    return {"job": job}


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    job = ctx.jobs.cancel_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found.")
    return {"job": job}


# --- Synchronous Generation & History ---


@router.get("/generations")
def list_generations(
    request: Request,
    voice_profile_id: str | None = Query(default=None),
    language: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    ctx = _ctx(request)
    items = ctx.db.list_generations(
        voice_profile_id=voice_profile_id,
        language=language,
        limit=limit,
    )
    return {"generations": [_serialize_generation(g) for g in items], "count": len(items)}


@router.post("/generations", status_code=201)
def create_generation(payload: GenerationCreateRequest, request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    profile, engine, cap, analysis, seg_dicts, gen_req, generation_id = (
        _validate_generation_inputs(ctx, payload)
    )
    now = datetime.now(timezone.utc)

    try:
        result = engine.generate(gen_req)
    except UnsupportedLanguageError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EngineUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except EngineError as exc:
        failed_rec = GenerationRecord(
            id=generation_id,
            voice_profile_id=profile.id,
            voice_profile_name=profile.display_name,
            text=analysis.normalized_text,
            language=payload.language,
            engine_id=cap.engine_id,
            model_id=cap.display_name,
            status="failed",
            audio_path="",
            duration_seconds=0.0,
            sample_rate_hz=24000,
            generation_time_seconds=0.0,
            speed=payload.speed,
            expression=payload.expression,
            segments=seg_dicts,
            error_message=str(exc),
            created_at=now,
        )
        ctx.db.create_generation(failed_rec)
        raise HTTPException(status_code=500, detail=f"Speech generation failed: {exc}") from exc

    record = GenerationRecord(
        id=generation_id,
        voice_profile_id=profile.id,
        voice_profile_name=profile.display_name,
        text=analysis.normalized_text,
        language=payload.language,
        engine_id=cap.engine_id,
        model_id=result.model_id,
        status="completed",
        audio_path=str(result.audio_path),
        duration_seconds=result.duration_seconds,
        sample_rate_hz=result.sample_rate_hz,
        generation_time_seconds=result.generation_time_seconds,
        speed=payload.speed,
        expression=payload.expression,
        segments=result.segments or seg_dicts,
        error_message="",
        created_at=now,
    )
    saved = ctx.db.create_generation(record)
    return {"generation": _serialize_generation(saved)}


# --- Dedicated Audio-to-Audio Voice Conversion ---


@router.post("/conversions", status_code=201)
async def convert_voice_audio(
    request: Request,
    source_file: UploadFile = File(...),
    voice_profile_id: str = Form(...),
    source_language: str = Form("en"),
) -> dict[str, Any]:
    """Explicit audio-to-audio Voice Conversion using OpenVoice v2 (separated from TTS)."""
    ctx = _ctx(request)
    profile = ctx.db.get_voice_profile(voice_profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Target voice profile was not found.")

    converter = ctx.engines.get("openvoice_v2_converter")
    cap = converter.capabilities()
    if not isinstance(converter, OpenVoiceV2ConverterEngine) or not cap.ready:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "voice_converter_not_ready",
                "engine_id": "openvoice_v2_converter",
                "message": cap.status_message,
                "missing_requirements": cap.missing_requirements,
            },
        )

    safe_name = sanitize_filename(source_file.filename or "source.wav")
    if not safe_name.lower().endswith(".wav"):
        raise HTTPException(status_code=400, detail="Source speech file must be a PCM WAV (.wav).")

    conversion_id = f"conv_{uuid.uuid4().hex[:10]}"
    temp_src = ctx.settings.cache_dir / f"{conversion_id}_src.wav"
    out_wav = ctx.storage.generation_audio_path(profile.id, conversion_id, ext="wav")
    try:
        data = await source_file.read()
        if not data or len(data) > ctx.settings.max_upload_bytes:
            raise HTTPException(status_code=400, detail="Invalid or oversized source WAV upload.")
        temp_src.write_bytes(data)
        insp = inspect_wav(temp_src)
        if not insp.is_valid:
            raise AudioValidationError("Uploaded source speech WAV failed validation.")

        prefs = ctx.db.get_preferences(default_engine=ctx.settings.tts_provider)
        dur, sr = converter.convert_audio(
            VoiceConversionRequest(
                source_audio_path=temp_src,
                target_reference_audio_path=Path(profile.reference_audio_path),
                output_path=out_wav,
                voice_profile_id=profile.id,
                compute_device=str(prefs.get("compute_device", "auto")),
            )
        )
    except AudioValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except EngineError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        temp_src.unlink(missing_ok=True)

    now = datetime.now(timezone.utc)
    rec = GenerationRecord(
        id=conversion_id,
        voice_profile_id=profile.id,
        voice_profile_name=profile.display_name,
        text=f"[Voice Conversion from {safe_name}]",
        language=source_language,
        engine_id="openvoice_v2_converter",
        model_id="myshell-ai/OpenVoiceV2 (Voice Conversion)",
        status="completed",
        audio_path=str(out_wav),
        duration_seconds=dur,
        sample_rate_hz=sr,
        generation_time_seconds=0.0,
        speed=1.0,
        expression="neutral",
        segments=[],
        error_message="",
        created_at=now,
    )
    saved = ctx.db.create_generation(rec)
    return {
        "conversion": _serialize_generation(saved),
        "experimental_warning": (
            "Urdu is not among OpenVoice v2's documented native languages; treat Urdu conversion as experimental."
            if source_language == "ur"
            else ""
        ),
    }


@router.get("/generations/{generation_id}")
def get_generation(generation_id: str, request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    rec = ctx.db.get_generation(generation_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Generation record not found.")
    return {"generation": _serialize_generation(rec)}


@router.get("/generations/{generation_id}/audio")
def stream_or_download_audio(
    generation_id: str,
    request: Request,
    format: str = Query(default="wav", pattern="^(wav|mp3)$"),
    download: int = Query(default=0, ge=0, le=1),
) -> FileResponse:
    ctx = _ctx(request)
    rec = ctx.db.get_generation(generation_id)
    if rec is None or not rec.audio_path:
        raise HTTPException(status_code=404, detail="Generated audio not found.")

    try:
        wav_path = ensure_within_dir(ctx.settings.generated_dir, Path(rec.audio_path))
    except StorageSecurityError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    if not wav_path.is_file():
        raise HTTPException(status_code=404, detail="Generated WAV file is missing on disk.")

    base_name = sanitize_filename(f"voicecity_{rec.voice_profile_name}_{rec.id}", rec.id)
    if format == "mp3":
        mp3_path = ctx.storage.generation_audio_path(rec.voice_profile_id, rec.id, ext="mp3")
        if not mp3_path.is_file():
            try:
                export_wav_to_mp3(wav_path, mp3_path)
            except AudioExportUnavailableError as exc:
                raise HTTPException(status_code=501, detail=str(exc)) from exc
        headers = (
            {"Content-Disposition": f'attachment; filename="{base_name}.mp3"'} if download else {}
        )
        return FileResponse(path=mp3_path, media_type="audio/mpeg", headers=headers)

    headers = (
        {"Content-Disposition": f'attachment; filename="{base_name}.wav"'} if download else {}
    )
    return FileResponse(path=wav_path, media_type="audio/wav", headers=headers)


@router.delete("/generations/{generation_id}")
def delete_generation(generation_id: str, request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    rec = ctx.db.get_generation(generation_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Generation record not found.")
    ctx.db.delete_generation(generation_id)
    try:
        ctx.storage.delete_generation_files(rec.voice_profile_id, rec.id)
    except StorageSecurityError:
        pass
    return {"deleted": True, "generation_id": generation_id}
