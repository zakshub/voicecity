"""Provider-neutral speech engine interface and metadata contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


class EngineError(RuntimeError):
    """Base error for speech engine failures."""


class EngineUnavailableError(EngineError):
    """Raised when the selected speech engine runtime or weights are not installed."""


class UnsupportedLanguageError(EngineError):
    """Raised when a language or mixed-language mode is unsupported by the active engine."""


@dataclass(frozen=True)
class EngineCapability:
    engine_id: str
    display_name: str
    version: str
    distributable_default: bool
    code_license: str
    weight_license: str
    commercial_compatible: bool
    commercial_note: str
    installed: bool
    ready: bool
    offline_supported: bool
    supported_languages: list[str]
    device: str
    estimated_download_gb: float
    local_weights_present: bool
    status_message: str
    source_url: str
    missing_requirements: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VoicePreparationResult:
    voice_profile_id: str
    reference_audio_path: Path
    ready: bool
    embedding_path: Path | None = None
    notes: str = ""


@dataclass(frozen=True)
class GenerationRequest:
    text: str
    language: str
    voice_profile_id: str
    reference_audio_path: Path
    output_path: Path
    output_format: str = "wav"
    speed: float = 1.0
    expression: str = "neutral"
    reference_transcript: str = ""
    compute_device: str = "auto"


@dataclass(frozen=True)
class GenerationResult:
    audio_path: Path
    duration_seconds: float
    sample_rate_hz: int
    model_id: str
    generation_time_seconds: float = 0.0
    segments: list[dict[str, str]] = field(default_factory=list)


class SpeechEngine(Protocol):
    @property
    def engine_id(self) -> str: ...

    def health_check(self) -> bool: ...

    def capabilities(self) -> EngineCapability: ...

    def supported_languages(self) -> set[str]: ...

    def prepare_voice(
        self,
        voice_profile_id: str,
        reference_audio_path: Path,
        work_dir: Path,
    ) -> VoicePreparationResult: ...

    def generate(self, request: GenerationRequest) -> GenerationResult: ...
