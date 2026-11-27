"""System health, truthful capabilities, hardware diagnostics, and local settings routes."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import SettingsUpdateRequest
from app.audio.service import mp3_export_available
from app.core.state import AppContext
from app.diagnostics.hardware import get_hardware_diagnostics

router = APIRouter()


def _ctx(request: Request) -> AppContext:
    return request.app.state.ctx  # type: ignore[no-any-return]


@router.get("/health")
def health(request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    prefs = ctx.db.get_preferences()
    active_engine = ctx.engines.resolve(str(prefs.get("active_engine") or ctx.settings.tts_provider))
    cap = active_engine.capabilities()
    return {
        "status": "ok",
        "service": "voicecity",
        "version": "0.2.0",
        "active_engine": cap.engine_id,
        "engine_ready": cap.ready,
        "local_only": not ctx.settings.allow_remote_inference,
    }


@router.get("/api/v1/capabilities")
def capabilities(request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    prefs = ctx.db.get_preferences()
    active_engine = ctx.engines.resolve(str(prefs.get("active_engine") or ctx.settings.tts_provider))
    cap = active_engine.capabilities()
    langs = set(cap.supported_languages)

    def _lang_status(code: str) -> str:
        if cap.ready and code in langs:
            return "available"
        if code in langs:
            return "engine_not_installed"
        return "unsupported_by_active_engine"

    mp3_ok = mp3_export_available()
    return {
        "voice_profiles": True,
        "audio_inspection": True,
        "reference_preparation": True,
        "speech_generation": cap.ready,
        "urdu": _lang_status("ur"),
        "english": _lang_status("en"),
        "mixed_language": _lang_status("mixed"),
        "export_formats": ["wav", "mp3"] if mp3_ok else ["wav"],
        "mp3_export_available": mp3_ok,
        "remote_inference": ctx.settings.allow_remote_inference,
        "active_engine": asdict(cap),
        "available_engines": [asdict(c) for c in ctx.engines.list_capabilities()],
        "message": cap.status_message,
    }


@router.get("/api/v1/diagnostics")
def diagnostics(request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    hw = get_hardware_diagnostics(target_path=ctx.settings.data_dir)
    prefs = ctx.db.get_preferences()
    profiles = ctx.db.list_voice_profiles()
    generations = ctx.db.list_generations(limit=500)
    return {
        "hardware": hw,
        "storage": {
            "data_dir": str(ctx.settings.data_dir),
            "model_dir": str(ctx.settings.model_dir),
            "db_path": str(ctx.settings.db_path),
            "voice_profile_count": len(profiles),
            "generation_count": len(generations),
        },
        "privacy": {
            "bind_host": ctx.settings.host,
            "remote_inference_enabled": ctx.settings.allow_remote_inference,
            "prefer_offline_only": bool(prefs.get("prefer_offline_only", True)),
        },
        "engines": [asdict(c) for c in ctx.engines.list_capabilities()],
    }


@router.get("/api/v1/settings")
def get_settings(request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    prefs = ctx.db.get_preferences()
    return {
        "preferences": prefs,
        "runtime": {
            "host": ctx.settings.host,
            "port": ctx.settings.port,
            "data_dir": str(ctx.settings.data_dir),
            "model_dir": str(ctx.settings.model_dir),
            "max_upload_mb": ctx.settings.max_upload_mb,
            "max_text_chars": ctx.settings.max_text_chars,
            "remote_inference_enabled": ctx.settings.allow_remote_inference,
            "mp3_export_available": mp3_export_available(),
        },
        "available_engines": [asdict(c) for c in ctx.engines.list_capabilities()],
    }


@router.patch("/api/v1/settings")
def update_settings(payload: SettingsUpdateRequest, request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    updates: dict[str, Any] = {}
    raw = payload.dict(exclude_none=True)
    if "active_engine" in raw:
        requested = str(raw["active_engine"])
        known = set(ctx.engines.list_ids()) | {"unconfigured"}
        if requested not in known:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown speech engine '{requested}'. Available: {sorted(known)}",
            )
    if raw.get("default_export_format") == "mp3" and not mp3_export_available():
        raise HTTPException(
            status_code=400,
            detail=(
                "MP3 export requires ffmpeg, which is not currently installed. "
                "Keep WAV as default or install ffmpeg first."
            ),
        )
    updates.update(raw)
    updated = ctx.db.update_preferences(updates)
    return {"preferences": updated}
