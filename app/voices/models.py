"""Provider-neutral metadata contract for a user-owned voice profile."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class VoiceProfile:
    id: str
    display_name: str
    source_audio_name: str
    source_duration_seconds: float
    source_sample_rate_hz: int
    source_channels: int
    created_at: datetime
    status: Literal["draft", "ready", "needs_review"]
