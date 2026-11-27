"""Provider-neutral domain contracts for user-owned voice profiles and speech generations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

ProfileStatus = Literal["draft", "ready", "needs_review"]
GenerationStatus = Literal["completed", "failed"]


@dataclass(frozen=True)
class VoiceProfile:
    id: str
    display_name: str
    source_audio_name: str
    source_duration_seconds: float
    source_sample_rate_hz: int
    source_channels: int
    created_at: datetime
    status: ProfileStatus
    notes: str = ""
    ownership_confirmed: bool = False
    source_audio_path: str = ""
    reference_audio_path: str = ""
    reference_transcript: str = ""
    source_bit_depth: int = 16
    peak_dbfs: float = -96.0
    rms_dbfs: float = -96.0
    clipping_samples: int = 0
    silence_ratio: float = 0.0
    reference_start_seconds: float = 0.0
    reference_duration_seconds: float = 0.0
    warnings: list[str] = field(default_factory=list)
    updated_at: datetime | None = None


@dataclass(frozen=True)
class GenerationRecord:
    id: str
    voice_profile_id: str
    voice_profile_name: str
    text: str
    language: str
    engine_id: str
    model_id: str
    status: GenerationStatus
    audio_path: str
    duration_seconds: float
    sample_rate_hz: int
    generation_time_seconds: float
    speed: float
    expression: str
    segments: list[dict[str, str]]
    created_at: datetime
    error_message: str = ""
