"""System health, separated capability reporting, model verification, diagnostics, and settings."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
from pathlib import Path
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
    prefs = ctx.db.get_preferences(default_engine=ctx.settings.tts_provider)
    active_engine = ctx.engines.resolve(str(prefs.get("active_engine") or ctx.settings.tts_provider))
    cap = active_engine.capabilities()
    return {
        "status": "ok",
        "service": "voicecity",
        "version": "0.3.0",
        "active_engine": cap.engine_id,
        "active_capability_class": cap.capability_class,
        "active_maturity_level": cap.maturity_level,
        "engine_ready": cap.ready,
        "local_only": not ctx.settings.allow_remote_inference,
    }


@router.get("/api/v1/capabilities")
def capabilities(request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    prefs = ctx.db.get_preferences(default_engine=ctx.settings.tts_provider)
    active_engine = ctx.engines.resolve(str(prefs.get("active_engine") or ctx.settings.tts_provider))
    cap = active_engine.capabilities()
    active_langs = set(active_engine.supported_languages()) if cap.ready else set()
    declared_langs = set(cap.supported_languages)

    def _active_lang_status(code: str) -> str:
        if cap.ready and code in active_langs:
            if code in cap.experimental_languages or cap.maturity_level == "experimental":
                return "ready_experimental"
            if cap.maturity_level == "empirically_verified":
                return "empirically_verified"
            return "ready_unverified_listening"
        if code in declared_langs:
            return "experimental_not_installed" if code in cap.experimental_languages else "not_installed"
        return "unsupported_by_active_engine"

    mp3_ok = mp3_export_available()
    cap_summary = ctx.engines.capability_summary()
    return {
        "voice_profiles": True,
        "audio_inspection": True,
        "reference_preparation": True,
        "speech_generation": cap.ready,
        "active_engine_uses_reference_audio": cap.uses_reference_audio,
        "urdu": _active_lang_status("ur"),
        "english": _active_lang_status("en"),
        "mixed_language": _active_lang_status("mixed"),
        "capabilities_by_type": cap_summary,
        "export_formats": ["wav", "mp3"] if mp3_ok else ["wav"],
        "mp3_export_available": mp3_ok,
        "remote_inference": ctx.settings.allow_remote_inference,
        "active_engine": asdict(cap),
        "available_engines": [asdict(c) for c in ctx.engines.list_capabilities()],
        "message": cap.status_message,
    }


@router.get("/api/v1/models/verify")
def verify_cached_models(request: Request) -> dict[str, Any]:
    """Inspect local VOICECITY_MODEL_DIR and verify cached files without touching network."""
    ctx = _ctx(request)
    model_dir = ctx.settings.model_dir
    expected_layout: dict[str, list[str]] = {
        "f5_tts_urdu": ["f5_tts_urdu/model_last.pt", "f5_tts_urdu/vocab.txt", "vocos/config.yaml"],
        "qwen3_tts_en": ["qwen3_tts_0.6b_base/config.json"],
        "indic_parler_tts": ["indic_parler_tts/config.json"],
        "openvoice_v2_converter": [
            "openvoice_v2/converter/checkpoint.pth",
            "openvoice_v2/converter/config.json",
        ],
    }

    checks: dict[str, dict[str, Any]] = {}
    for engine_id, rel_files in expected_layout.items():
        present: list[dict[str, Any]] = []
        missing: list[str] = []
        for rel in rel_files:
            full = model_dir / rel
            if full.is_file():
                size_bytes = full.stat().st_size
                sha_head = ""
                if size_bytes <= 5 * 1024 * 1024:
                    sha_head = hashlib.sha256(full.read_bytes()).hexdigest()[:16]
                present.append(
                    {
                        "path": rel,
                        "size_mb": round(size_bytes / (1024 * 1024), 2),
                        "sha256_prefix": sha_head or "large_file_skipped_in_fast_check",
                    }
                )
            else:
                missing.append(rel)
        checks[engine_id] = {
            "complete": len(missing) == 0,
            "present_files": present,
            "missing_files": missing,
        }

    return {
        "model_dir": str(model_dir),
        "models": checks,
    }


@router.get("/api/v1/diagnostics")
def diagnostics(request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    hw = get_hardware_diagnostics(target_path=ctx.settings.data_dir)
    prefs = ctx.db.get_preferences(default_engine=ctx.settings.tts_provider)
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
        "capabilities_by_type": ctx.engines.capability_summary(),
        "engines": [asdict(c) for c in ctx.engines.list_capabilities()],
    }


@router.get("/api/v1/settings")
def get_settings(request: Request) -> dict[str, Any]:
    ctx = _ctx(request)
    prefs = ctx.db.get_preferences(default_engine=ctx.settings.tts_provider)
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
    updated = ctx.db.update_preferences(raw)
    return {"preferences": updated}
