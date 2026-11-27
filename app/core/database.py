"""Local SQLite persistence for VoiceCity profiles, generation history, and preferences."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

from app.core.config import DEFAULT_ENGINE_ID
from app.voices.models import GenerationRecord, VoiceProfile

DEFAULT_USER_PREFERENCES: dict[str, Any] = {
    "active_engine": DEFAULT_ENGINE_ID,
    "compute_device": "auto",  # auto | cpu | cuda
    "default_language": "ur",  # ur | en | mixed
    "default_speed": 1.0,
    "default_expression": "neutral",  # neutral | clear | warm | calm
    "default_export_format": "wav",  # wav | mp3
    "prefer_offline_only": True,
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(raw: str | None) -> datetime:
    if not raw:
        return _utc_now()
    return datetime.fromisoformat(raw)


class VoiceCityDB:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS voice_profiles (
                    id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    ownership_confirmed INTEGER NOT NULL DEFAULT 0,
                    source_audio_name TEXT NOT NULL,
                    source_audio_path TEXT NOT NULL,
                    reference_audio_path TEXT NOT NULL DEFAULT '',
                    reference_transcript TEXT NOT NULL DEFAULT '',
                    source_duration_seconds REAL NOT NULL,
                    source_sample_rate_hz INTEGER NOT NULL,
                    source_channels INTEGER NOT NULL,
                    source_bit_depth INTEGER NOT NULL DEFAULT 16,
                    peak_dbfs REAL NOT NULL DEFAULT -96.0,
                    rms_dbfs REAL NOT NULL DEFAULT -96.0,
                    clipping_samples INTEGER NOT NULL DEFAULT 0,
                    silence_ratio REAL NOT NULL DEFAULT 0.0,
                    reference_start_seconds REAL NOT NULL DEFAULT 0.0,
                    reference_duration_seconds REAL NOT NULL DEFAULT 0.0,
                    warnings_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS generations (
                    id TEXT PRIMARY KEY,
                    voice_profile_id TEXT NOT NULL,
                    voice_profile_name TEXT NOT NULL,
                    text TEXT NOT NULL,
                    language TEXT NOT NULL,
                    engine_id TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    audio_path TEXT NOT NULL DEFAULT '',
                    duration_seconds REAL NOT NULL DEFAULT 0.0,
                    sample_rate_hz INTEGER NOT NULL DEFAULT 24000,
                    generation_time_seconds REAL NOT NULL DEFAULT 0.0,
                    speed REAL NOT NULL DEFAULT 1.0,
                    expression TEXT NOT NULL DEFAULT 'neutral',
                    segments_json TEXT NOT NULL DEFAULT '[]',
                    error_message TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (voice_profile_id)
                        REFERENCES voice_profiles(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    # --- Voice Profiles ---

    def _row_to_profile(self, row: sqlite3.Row) -> VoiceProfile:
        return VoiceProfile(
            id=str(row["id"]),
            display_name=str(row["display_name"]),
            notes=str(row["notes"]),
            ownership_confirmed=bool(row["ownership_confirmed"]),
            source_audio_name=str(row["source_audio_name"]),
            source_audio_path=str(row["source_audio_path"]),
            reference_audio_path=str(row["reference_audio_path"]),
            reference_transcript=str(row["reference_transcript"]),
            source_duration_seconds=float(row["source_duration_seconds"]),
            source_sample_rate_hz=int(row["source_sample_rate_hz"]),
            source_channels=int(row["source_channels"]),
            source_bit_depth=int(row["source_bit_depth"]),
            peak_dbfs=float(row["peak_dbfs"]),
            rms_dbfs=float(row["rms_dbfs"]),
            clipping_samples=int(row["clipping_samples"]),
            silence_ratio=float(row["silence_ratio"]),
            reference_start_seconds=float(row["reference_start_seconds"]),
            reference_duration_seconds=float(row["reference_duration_seconds"]),
            warnings=list(json.loads(row["warnings_json"] or "[]")),
            status=row["status"],
            created_at=_parse_dt(row["created_at"]),
            updated_at=_parse_dt(row["updated_at"]),
        )

    def create_voice_profile(self, profile: VoiceProfile) -> VoiceProfile:
        now = _utc_now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO voice_profiles (
                    id, display_name, notes, ownership_confirmed,
                    source_audio_name, source_audio_path, reference_audio_path,
                    reference_transcript, source_duration_seconds, source_sample_rate_hz,
                    source_channels, source_bit_depth, peak_dbfs, rms_dbfs,
                    clipping_samples, silence_ratio, reference_start_seconds,
                    reference_duration_seconds, warnings_json, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile.id,
                    profile.display_name,
                    profile.notes,
                    1 if profile.ownership_confirmed else 0,
                    profile.source_audio_name,
                    profile.source_audio_path,
                    profile.reference_audio_path,
                    profile.reference_transcript,
                    profile.source_duration_seconds,
                    profile.source_sample_rate_hz,
                    profile.source_channels,
                    profile.source_bit_depth,
                    profile.peak_dbfs,
                    profile.rms_dbfs,
                    profile.clipping_samples,
                    profile.silence_ratio,
                    profile.reference_start_seconds,
                    profile.reference_duration_seconds,
                    json.dumps(profile.warnings, ensure_ascii=False),
                    profile.status,
                    profile.created_at.isoformat(),
                    now,
                ),
            )
        return self.get_voice_profile(profile.id) or profile

    def list_voice_profiles(self) -> list[VoiceProfile]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM voice_profiles ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_profile(r) for r in rows]

    def get_voice_profile(self, profile_id: str) -> VoiceProfile | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM voice_profiles WHERE id = ?",
                (profile_id,),
            ).fetchone()
        return self._row_to_profile(row) if row else None

    def update_voice_profile(
        self,
        profile_id: str,
        *,
        display_name: str | None = None,
        notes: str | None = None,
        reference_transcript: str | None = None,
        reference_audio_path: str | None = None,
        reference_start_seconds: float | None = None,
        reference_duration_seconds: float | None = None,
        status: str | None = None,
        warnings: list[str] | None = None,
    ) -> VoiceProfile | None:
        existing = self.get_voice_profile(profile_id)
        if existing is None:
            return None

        now = _utc_now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE voice_profiles
                SET display_name = ?,
                    notes = ?,
                    reference_transcript = ?,
                    reference_audio_path = ?,
                    reference_start_seconds = ?,
                    reference_duration_seconds = ?,
                    status = ?,
                    warnings_json = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    display_name if display_name is not None else existing.display_name,
                    notes if notes is not None else existing.notes,
                    (
                        reference_transcript
                        if reference_transcript is not None
                        else existing.reference_transcript
                    ),
                    (
                        reference_audio_path
                        if reference_audio_path is not None
                        else existing.reference_audio_path
                    ),
                    (
                        reference_start_seconds
                        if reference_start_seconds is not None
                        else existing.reference_start_seconds
                    ),
                    (
                        reference_duration_seconds
                        if reference_duration_seconds is not None
                        else existing.reference_duration_seconds
                    ),
                    status if status is not None else existing.status,
                    json.dumps(
                        warnings if warnings is not None else existing.warnings,
                        ensure_ascii=False,
                    ),
                    now,
                    profile_id,
                ),
            )
        return self.get_voice_profile(profile_id)

    def delete_voice_profile(self, profile_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM voice_profiles WHERE id = ?", (profile_id,))
            return cur.rowcount > 0

    # --- Generations ---

    def _row_to_generation(self, row: sqlite3.Row) -> GenerationRecord:
        return GenerationRecord(
            id=str(row["id"]),
            voice_profile_id=str(row["voice_profile_id"]),
            voice_profile_name=str(row["voice_profile_name"]),
            text=str(row["text"]),
            language=str(row["language"]),
            engine_id=str(row["engine_id"]),
            model_id=str(row["model_id"]),
            status=row["status"],
            audio_path=str(row["audio_path"]),
            duration_seconds=float(row["duration_seconds"]),
            sample_rate_hz=int(row["sample_rate_hz"]),
            generation_time_seconds=float(row["generation_time_seconds"]),
            speed=float(row["speed"]),
            expression=str(row["expression"]),
            segments=list(json.loads(row["segments_json"] or "[]")),
            error_message=str(row["error_message"]),
            created_at=_parse_dt(row["created_at"]),
        )

    def create_generation(self, record: GenerationRecord) -> GenerationRecord:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO generations (
                    id, voice_profile_id, voice_profile_name, text, language,
                    engine_id, model_id, status, audio_path, duration_seconds,
                    sample_rate_hz, generation_time_seconds, speed, expression,
                    segments_json, error_message, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.voice_profile_id,
                    record.voice_profile_name,
                    record.text,
                    record.language,
                    record.engine_id,
                    record.model_id,
                    record.status,
                    record.audio_path,
                    record.duration_seconds,
                    record.sample_rate_hz,
                    record.generation_time_seconds,
                    record.speed,
                    record.expression,
                    json.dumps(record.segments, ensure_ascii=False),
                    record.error_message,
                    record.created_at.isoformat(),
                ),
            )
        return self.get_generation(record.id) or record

    def list_generations(
        self,
        *,
        voice_profile_id: str | None = None,
        language: str | None = None,
        limit: int = 100,
    ) -> list[GenerationRecord]:
        clauses: list[str] = []
        params: list[Any] = []
        if voice_profile_id:
            clauses.append("voice_profile_id = ?")
            params.append(voice_profile_id)
        if language:
            clauses.append("language = ?")
            params.append(language)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(max(1, min(limit, 500)))
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM generations {where} ORDER BY created_at DESC LIMIT ?",
                params,
            ).fetchall()
        return [self._row_to_generation(r) for r in rows]

    def get_generation(self, generation_id: str) -> GenerationRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM generations WHERE id = ?",
                (generation_id,),
            ).fetchone()
        return self._row_to_generation(row) if row else None

    def delete_generation(self, generation_id: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM generations WHERE id = ?", (generation_id,))
            return cur.rowcount > 0

    # --- Settings ---

    def get_preferences(self, default_engine: str | None = None) -> dict[str, Any]:
        prefs = dict(DEFAULT_USER_PREFERENCES)
        if default_engine:
            prefs["active_engine"] = default_engine
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value_json FROM app_settings").fetchall()
        for row in rows:
            key = str(row["key"])
            if key in prefs:
                prefs[key] = json.loads(row["value_json"])
        return prefs

    def update_preferences(self, updates: dict[str, Any]) -> dict[str, Any]:
        now = _utc_now().isoformat()
        with self._connect() as conn:
            for key, value in updates.items():
                if key not in DEFAULT_USER_PREFERENCES:
                    continue
                conn.execute(
                    """
                    INSERT INTO app_settings (key, value_json, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value_json = excluded.value_json,
                        updated_at = excluded.updated_at
                    """,
                    (key, json.dumps(value), now),
                )
        return self.get_preferences()
