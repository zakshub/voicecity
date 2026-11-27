"""Provider-neutral speech engine interface with strict capability and maturity separation.

Every adapter must explicitly declare:
- capability_class: 'standard_tts' | 'reference_voice_cloning' | 'voice_conversion'
                    | 'cross_linguistic_voice_conversion'
- maturity_level:   'experimental' | 'technically_integrated' | 'empirically_verified'
- uses_reference_audio: whether the model actually conditions on user reference audio
- license_category: 'permissive_commercial' | 'share_alike_optional'
                    | 'non_commercial_restricted' | 'none'
- verification_status: separate booleans for automated tests, model integration,
                       actual speech generated, human listening, and commercial licensing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal, Protocol

CapabilityClass = Literal[
    "standard_tts",
    "reference_voice_cloning",
    "voice_conversion",
    "cross_linguistic_voice_conversion",
]

MaturityLevel = Literal[
    "experimental",
    "technically_integrated",
    "empirically_verified",
]

LicenseCategory = Literal[
    "permissive_commercial",
    "share_alike_optional",
    "non_commercial_restricted",
    "none",
]


class EngineError(RuntimeError):
    """Base error for speech engine failures."""


class EngineUnavailableError(EngineError):
    """Raised when the selected speech engine runtime or weights are not installed."""


class UnsupportedLanguageError(EngineError):
    """Raised when a language or mixed-language mode is unsupported by the active engine."""


class GenerationCancelledError(EngineError):
    """Raised when a queued or active generation job is cancelled by the user."""


@dataclass(frozen=True)
class VerificationStatus:
    automated_tests_passed: bool
    model_integration_verified: bool
    actual_speech_generated: bool
    human_listening_completed: bool
    commercial_licensing_verified: bool


@dataclass(frozen=True)
class EngineCapability:
    engine_id: str
    display_name: str
    version: str
    capability_class: CapabilityClass
    maturity_level: MaturityLevel
    uses_reference_audio: bool
    requires_reference_transcript: bool
    distributable_default: bool
    license_category: LicenseCategory
    code_license: str
    weight_license: str
    commercial_compatible: bool
    commercial_note: str
    installed: bool
    ready: bool
    offline_supported: bool
    supported_languages: list[str]
    verified_native_languages: list[str]
    experimental_languages: list[str]
    device: str
    estimated_download_gb: float
    min_ram_gb: int
    min_vram_gb: int | None
    cpu_feasible: str
    local_weights_present: bool
    status_message: str
    source_url: str
    license_url: str
    verification: VerificationStatus
    missing_requirements: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)


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
    progress_callback: Callable[[int, str], None] | None = None
    cancel_check: Callable[[], bool] | None = None


@dataclass(frozen=True)
class VoiceConversionRequest:
    source_audio_path: Path
    target_reference_audio_path: Path
    output_path: Path
    voice_profile_id: str
    compute_device: str = "auto"


@dataclass(frozen=True)
class GenerationResult:
    audio_path: Path
    duration_seconds: float
    sample_rate_hz: int
    model_id: str
    generation_time_seconds: float = 0.0
    segments: list[dict[str, str]] = field(default_factory=list)
    capability_used: CapabilityClass = "reference_voice_cloning"


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
