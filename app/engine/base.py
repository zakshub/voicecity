"""Provider-neutral speech engine interface."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class GenerationRequest:
    text: str
    language: str
    voice_profile_id: str
    output_format: str = "wav"


@dataclass(frozen=True)
class GenerationResult:
    audio_path: Path
    duration_seconds: float
    sample_rate_hz: int
    model_id: str


class SpeechEngine(Protocol):
    def health_check(self) -> bool: ...

    def supported_languages(self) -> set[str]: ...

    def generate(self, request: GenerationRequest) -> GenerationResult: ...
