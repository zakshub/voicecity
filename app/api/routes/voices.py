"""Voice profile import, audio inspection, preparation, streaming, and deletion routes."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.api.schemas import PrepareVoiceRequest, VoiceProfileUpdateRequest
from app.audio.service import AudioValidationError, inspect_wav, prepare_reference_segment
from app.core.state import AppContext
from app.core.storage import StorageSecurityError, ensure_within_dir, sanitize_filename
from app.voices.models import VoiceProfile

router = APIRouter(prefix="/api/v1/voices", tags=["voices"])


def _ctx(request: Request) -> AppContext:
    return request.app.state.ctx  # type: ignore[no-any-return]


def _serialize_profile(profile: VoiceProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "display_name": profile.display_name,
        "notes": profile.notes,
        "ownership_confirmed": profile.ownership_confirmed,
        "source_audio_name": profile.source_audio_name,
        "source_duration_seconds": profile.source_duration_seconds,
        "source_sample_rate_hz": profile.source_sample_rate_hz,
        "source_channels": profile.source_channels,
        "source_bit_depth": profile.source_bit_depth,
        "peak_dbfs": profile.peak_dbfs,
        "rms_dbfs": profile.rms_dbfs,
        "clipping_samples": profile.clipping_samples,
        "silence_ratio": profile.silence_ratio,
        "reference_start_seconds": profile.reference_start_seconds,
        "reference_duration_seconds": profile.reference_duration_seconds,
        "reference_transcript": profile.reference_transcript,
        "has_reference_segment": bool(
            profile.reference_audio_path and Path(profile.reference_audio_path).is_file()
        ),
        "warnings": profile.warnings,
        "status": profile.status,
        "source_audio_url": f"/api/v1/voices/{profile.id}/source-audio",
        "reference_audio_url": f"/api/v1/voices/{profile.id}/reference-audio",
        "created_at": profile.created_at.isoformat(),
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


@router.get("")
def list_voices(request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    profiles = ctx.db.list_voice_profiles()
    return {"voices": [_serialize_profile(p) for p in profiles], "count": len(profiles)}


@router.post("/import", status_code=201)
async def import_voice(
    request: Request,
    file: UploadFile = File(...),
    display_name: str = Form(...),
    ownership_confirmed: bool = Form(False),
    notes: str = Form(""),
    reference_transcript: str = Form(""),
    target_reference_seconds: float = Form(8.0),
) -> dict[str, Any]:
    ctx = _ctx(request)
    clean_name = display_name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Voice profile display name is required.")
    if not ownership_confirmed:
        raise HTTPException(
            status_code=400,
            detail=(
                "Ownership and authorization confirmation is required. VoiceCity is intended "
                "for your own voice or a voice you are explicitly authorized to use."
            ),
        )

    safe_filename = sanitize_filename(file.filename or "recording.wav")
    if not safe_filename.lower().endswith(".wav"):
        raise HTTPException(
            status_code=400,
            detail=(
                "Only uncompressed WAV recordings (.wav) are supported for voice profile import. "
                "Convert your file to WAV before uploading."
            ),
        )

    target_sec = max(3.0, min(15.0, float(target_reference_seconds)))
    profile_id = f"vp_{uuid.uuid4().hex[:12]}"
    source_path = ctx.storage.source_audio_path(profile_id)
    ref_path = ctx.storage.reference_audio_path(profile_id)

    # Stream upload with strict byte size limit
    written = 0
    max_bytes = ctx.settings.max_upload_bytes
    try:
        with source_path.open("wb") as out_fh:
            while True:
                chunk = await file.read(1024 * 256)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"Audio upload exceeds the {ctx.settings.max_upload_mb} MB limit. "
                            "Use a shorter or mono 24-48 kHz WAV recording."
                        ),
                    )
                out_fh.write(chunk)

        if written == 0:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

        inspection = inspect_wav(source_path)
        if not inspection.is_valid:
            raise AudioValidationError(
                "Uploaded WAV recording failed validation: "
                + (" ".join(inspection.warnings) or "audio is too short or silent.")
            )

        prepared = prepare_reference_segment(
            source_path=source_path,
            output_path=ref_path,
            target_duration_sec=target_sec,
            target_sample_rate=24000,
        )
    except HTTPException:
        ctx.storage.delete_profile_files(profile_id)
        raise
    except AudioValidationError as exc:
        ctx.storage.delete_profile_files(profile_id)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        ctx.storage.delete_profile_files(profile_id)
        raise HTTPException(
            status_code=500, detail=f"Failed to process uploaded recording: {exc}"
        ) from exc

    all_warnings = list(inspection.warnings) + list(prepared.warnings)
    status = "ready" if inspection.quality_status == "good" else "needs_review"

    # Optional engine-level voice preparation if an ML engine is ready
    prefs = ctx.db.get_preferences()
    active_engine = ctx.engines.resolve(str(prefs.get("active_engine") or ctx.settings.tts_provider))
    if active_engine.capabilities().ready:
        try:
            active_engine.prepare_voice(
                voice_profile_id=profile_id,
                reference_audio_path=ref_path,
                work_dir=ctx.storage.profile_dir(profile_id),
            )
        except Exception as exc:
            all_warnings.append(f"Engine voice preparation warning: {exc}")

    now = datetime.now(timezone.utc)
    profile = VoiceProfile(
        id=profile_id,
        display_name=clean_name[:120],
        notes=notes.strip()[:1000],
        ownership_confirmed=True,
        source_audio_name=safe_filename,
        source_audio_path=str(source_path),
        reference_audio_path=str(ref_path),
        reference_transcript=reference_transcript.strip()[:2000],
        source_duration_seconds=inspection.duration_seconds,
        source_sample_rate_hz=inspection.sample_rate_hz,
        source_channels=inspection.channels,
        source_bit_depth=inspection.bit_depth,
        peak_dbfs=inspection.peak_dbfs,
        rms_dbfs=inspection.rms_dbfs,
        clipping_samples=inspection.clipping_samples,
        silence_ratio=inspection.silence_ratio,
        reference_start_seconds=prepared.start_seconds,
        reference_duration_seconds=prepared.duration_seconds,
        warnings=all_warnings,
        status=status,  # type: ignore[arg-type]
        created_at=now,
        updated_at=now,
    )
    saved = ctx.db.create_voice_profile(profile)
    serialized = _serialize_profile(saved)
    ctx.storage.write_profile_manifest(profile_id, serialized)
    return {"voice": serialized}


@router.get("/{voice_id}")
def get_voice(voice_id: str, request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    profile = ctx.db.get_voice_profile(voice_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Voice profile not found.")
    return {"voice": _serialize_profile(profile)}


@router.patch("/{voice_id}")
def update_voice(
    voice_id: str, payload: VoiceProfileUpdateRequest, request: Request
) -> dict[str, Any]:
    ctx = _ctx(request)
    updated = ctx.db.update_voice_profile(
        voice_id,
        display_name=payload.display_name.strip() if payload.display_name is not None else None,
        notes=payload.notes.strip() if payload.notes is not None else None,
        reference_transcript=(
            payload.reference_transcript.strip()
            if payload.reference_transcript is not None
            else None
        ),
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Voice profile not found.")
    serialized = _serialize_profile(updated)
    ctx.storage.write_profile_manifest(voice_id, serialized)
    return {"voice": serialized}


@router.post("/{voice_id}/prepare")
def reprepare_voice(
    voice_id: str, payload: PrepareVoiceRequest, request: Request
) -> dict[str, Any]:
    ctx = _ctx(request)
    profile = ctx.db.get_voice_profile(voice_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Voice profile not found.")

    try:
        source_path = ensure_within_dir(
            ctx.settings.voice_profiles_dir, Path(profile.source_audio_path)
        )
        ref_path = ctx.storage.reference_audio_path(voice_id)
        prepared = prepare_reference_segment(
            source_path=source_path,
            output_path=ref_path,
            target_duration_sec=payload.target_duration_seconds,
            target_sample_rate=24000,
        )
    except (StorageSecurityError, AudioValidationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    prefs = ctx.db.get_preferences()
    active_engine = ctx.engines.resolve(str(prefs.get("active_engine") or ctx.settings.tts_provider))
    engine_note = ""
    if active_engine.capabilities().ready:
        prep_res = active_engine.prepare_voice(
            voice_profile_id=voice_id,
            reference_audio_path=ref_path,
            work_dir=ctx.storage.profile_dir(voice_id),
        )
        engine_note = prep_res.notes

    updated = ctx.db.update_voice_profile(
        voice_id,
        reference_audio_path=str(ref_path),
        reference_start_seconds=prepared.start_seconds,
        reference_duration_seconds=prepared.duration_seconds,
        reference_transcript=(
            payload.reference_transcript.strip()
            if payload.reference_transcript is not None
            else profile.reference_transcript
        ),
        status="ready",
    )
    assert updated is not None
    serialized = _serialize_profile(updated)
    ctx.storage.write_profile_manifest(voice_id, serialized)
    return {"voice": serialized, "engine_note": engine_note}


@router.get("/{voice_id}/source-audio")
def stream_source_audio(voice_id: str, request: Request) -> FileResponse:
    ctx = _ctx(request)
    profile = ctx.db.get_voice_profile(voice_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Voice profile not found.")
    try:
        safe_path = ensure_within_dir(
            ctx.settings.voice_profiles_dir, Path(profile.source_audio_path)
        )
    except StorageSecurityError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not safe_path.is_file():
        raise HTTPException(status_code=404, detail="Original source audio file is missing on disk.")
    return FileResponse(path=safe_path, media_type="audio/wav", filename=profile.source_audio_name)


@router.get("/{voice_id}/reference-audio")
def stream_reference_audio(voice_id: str, request: Request) -> FileResponse:
    ctx = _ctx(request)
    profile = ctx.db.get_voice_profile(voice_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Voice profile not found.")
    try:
        safe_path = ensure_within_dir(
            ctx.settings.voice_profiles_dir, Path(profile.reference_audio_path)
        )
    except StorageSecurityError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if not safe_path.is_file():
        raise HTTPException(
            status_code=404, detail="Prepared reference audio segment is missing on disk."
        )
    return FileResponse(
        path=safe_path,
        media_type="audio/wav",
        filename=f"{sanitize_filename(profile.display_name, 'voice')}_reference.wav",
    )


@router.delete("/{voice_id}")
def delete_voice(voice_id: str, request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    profile = ctx.db.get_voice_profile(voice_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Voice profile not found.")
    ctx.db.delete_voice_profile(voice_id)
    try:
        ctx.storage.delete_profile_files(voice_id)
    except StorageSecurityError:
        pass
    return {"deleted": True, "voice_id": voice_id}
