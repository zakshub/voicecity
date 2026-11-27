"""Safe fallback adapter reporting truthful unavailable status when no engine is configured."""

from __future__ import annotations

from pathlib import Path

from app.engine.base import (
    EngineCapability,
    EngineUnavailableError,
    GenerationRequest,
    GenerationResult,
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
            display_name="No Speech Engine Configured",
            version="0.0.0",
            distributable_default=False,
            code_license="N/A",
            weight_license="N/A",
            commercial_compatible=True,
            commercial_note="No third-party weights loaded.",
            installed=False,
            ready=False,
            offline_supported=True,
            supported_languages=[],
            device="none",
            estimated_download_gb=0.0,
            local_weights_present=False,
            status_message=(
                "No speech engine is active. Install a commercially compatible local model "
                "on Linux Mint using scripts/install_linux_mint.sh and scripts/download_models.py."
            ),
            source_url="https://github.com/zakshub/voicecity",
            missing_requirements=["Local speech engine runtime and model weights"],
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
            notes="Reference WAV is prepared locally, but no ML speech engine is installed yet.",
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        raise EngineUnavailableError(
            "No local speech engine is installed or configured. Run the Linux Mint setup and "
            "model download scripts before generating speech."
        )
