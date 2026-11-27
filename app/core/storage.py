"""Confined local filesystem storage for voice profiles, generated audio, and cache."""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil

from app.core.config import Settings

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")
_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{4,64}$")


class StorageSecurityError(ValueError):
    """Raised when a path escapes the configured local data directory or ID is invalid."""


def sanitize_filename(filename: str, fallback: str = "recording.wav") -> str:
    base = Path(filename).name.strip()
    cleaned = _SAFE_NAME_RE.sub("_", base).strip("._")
    if not cleaned:
        return fallback
    return cleaned[:120]


def validate_entity_id(entity_id: str) -> str:
    if not _SAFE_ID_RE.match(entity_id):
        raise StorageSecurityError(f"Invalid identifier format: {entity_id!r}")
    return entity_id


def ensure_within_dir(base_dir: Path, target_path: Path) -> Path:
    resolved_base = base_dir.resolve()
    resolved_target = target_path.resolve()
    try:
        resolved_target.relative_to(resolved_base)
    except ValueError as exc:
        raise StorageSecurityError("Resolved path escapes configured data directory.") from exc
    return resolved_target


class LocalStorage:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.ensure_directories()

    def ensure_directories(self) -> None:
        for path in (
            self.settings.data_dir,
            self.settings.voice_profiles_dir,
            self.settings.generated_dir,
            self.settings.cache_dir,
            self.settings.model_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def profile_dir(self, profile_id: str) -> Path:
        safe_id = validate_entity_id(profile_id)
        target = ensure_within_dir(
            self.settings.voice_profiles_dir,
            self.settings.voice_profiles_dir / safe_id,
        )
        target.mkdir(parents=True, exist_ok=True)
        return target

    def source_audio_path(self, profile_id: str) -> Path:
        return ensure_within_dir(
            self.settings.voice_profiles_dir,
            self.profile_dir(profile_id) / "source_audio.wav",
        )

    def reference_audio_path(self, profile_id: str) -> Path:
        return ensure_within_dir(
            self.settings.voice_profiles_dir,
            self.profile_dir(profile_id) / "reference_segment.wav",
        )

    def write_profile_manifest(self, profile_id: str, payload: dict[str, object]) -> Path:
        manifest_path = ensure_within_dir(
            self.settings.voice_profiles_dir,
            self.profile_dir(profile_id) / "profile.json",
        )
        manifest_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return manifest_path

    def delete_profile_files(self, profile_id: str) -> None:
        safe_id = validate_entity_id(profile_id)
        prof_dir = ensure_within_dir(
            self.settings.voice_profiles_dir,
            self.settings.voice_profiles_dir / safe_id,
        )
        if prof_dir.exists():
            shutil.rmtree(prof_dir, ignore_errors=True)

        gen_dir = ensure_within_dir(
            self.settings.generated_dir,
            self.settings.generated_dir / safe_id,
        )
        if gen_dir.exists():
            shutil.rmtree(gen_dir, ignore_errors=True)

    def generation_audio_path(
        self, profile_id: str, generation_id: str, ext: str = "wav"
    ) -> Path:
        safe_prof = validate_entity_id(profile_id)
        safe_gen = validate_entity_id(generation_id)
        safe_ext = "mp3" if ext.lower() == "mp3" else "wav"
        parent = ensure_within_dir(
            self.settings.generated_dir,
            self.settings.generated_dir / safe_prof,
        )
        parent.mkdir(parents=True, exist_ok=True)
        return ensure_within_dir(self.settings.generated_dir, parent / f"{safe_gen}.{safe_ext}")

    def delete_generation_files(self, profile_id: str, generation_id: str) -> None:
        for ext in ("wav", "mp3"):
            path = self.generation_audio_path(profile_id, generation_id, ext=ext)
            if path.is_file():
                path.unlink(missing_ok=True)
