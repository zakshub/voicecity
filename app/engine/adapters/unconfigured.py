"""Safe fallback adapter reporting truthful unavailable status when no engine is active."""

from __future__ import annotations

from pathlib import Path

from app.engine.base import (
    EngineCapability,
    EngineUnavailableError,
    GenerationRequest,
    GenerationResult,
    VerificationStatus,
    VoicePreparationResult,
)


class UnconfiguredEngine:
    @property
    def engine_id(self) -> str:
        return "unconfigured"

    def health_check(self) -> bool:
        return False

    def capabilities(self) -> EngineCapability:
        return EngineCapability(
            engine_id=self.engine_id,
            display_name="No Speech Engine Active",
            version="0.0.0",
            capability_class="reference_voice_cloning",
            maturity_level="technically_integrated",
            uses_reference_audio=False,
            requires_reference_transcript=False,
            distributable_default=False,
            license_category="none",
            code_license="N/A",
            weight_license="N/A",
            commercial_compatible=True,
            commercial_note="No third-party weights loaded.",
            installed=False,
            ready=False,
            offline_supported=True,
            supported_languages=[],
            verified_native_languages=[],
            experimental_languages=[],
            device="none",
            estimated_download_gb=0.0,
            min_ram_gb=2,
            min_vram_gb=None,
            cpu_feasible="N/A",
            local_weights_present=False,
            status_message=(
                "No speech engine is installed or selected yet. Select an engine in Settings "
                "and install its runtime + weights on Linux Mint."
            ),
            source_url="https://github.com/zakshub/voicecity",
            license_url="https://github.com/zakshub/voicecity/blob/main/docs/MODEL_LICENSING_REGISTER.md",
            verification=VerificationStatus(
                automated_tests_passed=True,
                model_integration_verified=False,
                actual_speech_generated=False,
                human_listening_completed=False,
                commercial_licensing_verified=True,
            ),
            missing_requirements=["Install a local speech engine runtime and cache weights on Linux Mint"],
        )

    def supported_languages(self) -> set[str]:
        return set()

    def prepare_voice(
        self,
        voice_profile_id: str,
        reference_audio_path: Path,
        work_dir: Path,
    ) -> VoicePreparationResult:
        return VoicePreparationResult(
            voice_profile_id=voice_profile_id,
            reference_audio_path=reference_audio_path,
            ready=False,
            notes="Reference WAV is prepared locally, but no speech engine is active yet.",
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        raise EngineUnavailableError(
            "No local speech engine is installed or configured. Select an engine in Settings "
            "and install its runtime and weights on your Linux Mint laptop."
        )
