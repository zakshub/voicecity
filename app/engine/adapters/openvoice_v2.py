"""Voice tone-color conversion ONLY: MyShell OpenVoice v2 (MIT).

IMPORTANT HONEST BOUNDARY:
- Capability Class: voice_conversion (audio-to-audio tone-color transfer; NOT standalone TTS)
- Documented native V2 languages: English, Spanish, French, Chinese, Japanese, Korean.
- Urdu is NOT among OpenVoice v2's documented native languages. Applying this converter to
  Urdu audio is experimental cross-linguistic conversion and must never be labelled verified
  native Urdu voice cloning.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from app.audio.service import inspect_wav
from app.engine.base import (
    EngineCapability,
    EngineError,
    EngineUnavailableError,
    GenerationRequest,
    GenerationResult,
    VerificationStatus,
    VoiceConversionRequest,
    VoicePreparationResult,
)


class OpenVoiceV2ConverterEngine:
    def __init__(self, model_dir: Path) -> None:
        self.model_dir = model_dir.resolve()
        self._converter_dir = self.model_dir / "openvoice_v2" / "converter"
        self._loaded_device: str | None = None
        self._converter: Any = None

    @property
    def engine_id(self) -> str:
        return "openvoice_v2_converter"

    def _missing_modules(self) -> list[str]:
        required = ("torch", "openvoice", "soundfile")
        return [m for m in required if importlib.util.find_spec(m) is None]

    def _weights_present(self) -> tuple[bool, list[str]]:
        missing: list[str] = []
        if not (self._converter_dir / "checkpoint.pth").is_file():
            missing.append(f"OpenVoice v2 checkpoint ({self._converter_dir / 'checkpoint.pth'})")
        if not (self._converter_dir / "config.json").is_file():
            missing.append(f"OpenVoice v2 config ({self._converter_dir / 'config.json'})")
        return len(missing) == 0, missing

    def _detect_device(self, preferred: str = "auto") -> str:
        if preferred == "cpu":
            return "cpu"
        if importlib.util.find_spec("torch") is not None:
            try:
                import torch

                if torch.cuda.is_available():
                    return "cuda"
            except Exception:
                return "cpu"
        return "cpu"

    def health_check(self) -> bool:
        return self.capabilities().ready

    def supported_languages(self) -> set[str]:
        return {"en"}

    def capabilities(self) -> EngineCapability:
        missing_mods = self._missing_modules()
        weights_ok, missing_weights = self._weights_present()
        installed = len(missing_mods) == 0
        ready = installed and weights_ok
        missing_all = [f"Python module: {m}" for m in missing_mods] + missing_weights

        if ready:
            status_msg = (
                "OpenVoice v2 Tone Color Converter (MIT) is cached locally for audio-to-audio "
                "voice conversion. Documented native V2 languages: EN, ES, FR, ZH, JA, KO (Urdu is NOT native)."
            )
        elif not installed:
            status_msg = (
                "OpenVoice v2 runtime is not installed. Run "
                "'bash scripts/install_linux_mint.sh --with-engine openvoice_v2_converter --device auto'."
            )
        else:
            status_msg = (
                "OpenVoice v2 runtime is installed, but converter checkpoint (~131 MB) is missing. "
                "Run 'python scripts/download_models.py --engine openvoice_v2_converter'."
            )

        return EngineCapability(
            engine_id=self.engine_id,
            display_name="MyShell OpenVoice v2 (Voice Conversion ONLY · Not Standalone TTS)",
            version="2.0.0",
            capability_class="voice_conversion",
            maturity_level="technically_integrated",
            uses_reference_audio=True,
            requires_reference_transcript=False,
            distributable_default=False,
            license_category="permissive_commercial",
            code_license="MIT (myshell-ai/OpenVoice)",
            weight_license="MIT (myshell-ai/OpenVoiceV2)",
            commercial_compatible=True,
            commercial_note="Permissive MIT code & weights. Voice conversion component only; Urdu is NOT native.",
            installed=installed,
            ready=ready,
            offline_supported=True,
            supported_languages=["en"],
            verified_native_languages=["en"],
            experimental_languages=["ur"],
            device=self._detect_device("auto"),
            estimated_download_gb=0.14,
            min_ram_gb=4,
            min_vram_gb=2,
            cpu_feasible="Usable on CPU (slower than GPU; se_extractor requires CPU device mapping)",
            local_weights_present=weights_ok,
            status_message=status_msg,
            source_url="https://github.com/myshell-ai/OpenVoice",
            license_url="https://github.com/myshell-ai/OpenVoice/blob/main/LICENSE",
            verification=VerificationStatus(
                automated_tests_passed=True,
                model_integration_verified=False,
                actual_speech_generated=False,
                human_listening_completed=False,
                commercial_licensing_verified=True,
            ),
            missing_requirements=missing_all,
            caveats=[
                "Audio-to-audio voice converter ONLY — requires an existing source speech WAV file.",
                "Urdu is NOT among OpenVoice v2's 6 documented native languages (EN, ES, FR, ZH, JA, KO).",
                "Cross-linguistic tone transfer on Urdu speech is experimental and unverified.",
            ],
        )

    def _ensure_loaded(self, preferred_device: str = "auto") -> str:
        cap = self.capabilities()
        if not cap.ready:
            raise EngineUnavailableError(
                f"{cap.status_message} Missing: {', '.join(cap.missing_requirements)}"
            )
        device = self._detect_device(preferred_device)
        if self._converter is not None and self._loaded_device == device:
            return device
        try:
            from openvoice.api import ToneColorConverter

            converter = ToneColorConverter(
                str(self._converter_dir / "config.json"),
                device=device,
            )
            converter.load_ckpt(str(self._converter_dir / "checkpoint.pth"))
            self._converter = converter
            self._loaded_device = device
            return device
        except Exception as exc:
            raise EngineError(f"Failed to load OpenVoice v2 converter: {exc}") from exc

    def prepare_voice(
        self,
        voice_profile_id: str,
        reference_audio_path: Path,
        work_dir: Path,
    ) -> VoicePreparationResult:
        cap = self.capabilities()
        if not cap.ready:
            return VoicePreparationResult(
                voice_profile_id=voice_profile_id,
                reference_audio_path=reference_audio_path,
                ready=False,
                notes=cap.status_message,
            )
        self._ensure_loaded("auto")
        emb_path = work_dir / "openvoice_se.pth"
        try:
            from openvoice import se_extractor
            import torch

            target_se, _ = se_extractor.get_se(
                str(reference_audio_path), self._converter, vad=False
            )
            torch.save(target_se, str(emb_path))
            return VoicePreparationResult(
                voice_profile_id=voice_profile_id,
                reference_audio_path=reference_audio_path,
                ready=True,
                embedding_path=emb_path,
                notes="Extracted OpenVoice v2 tone-color embedding locally.",
            )
        except Exception as exc:
            raise EngineError(f"OpenVoice v2 speaker embedding extraction failed: {exc}") from exc

    def convert_audio(self, request: VoiceConversionRequest) -> tuple[float, int]:
        device = self._ensure_loaded(request.compute_device)
        try:
            from openvoice import se_extractor
            import torch

            emb_path = request.target_reference_audio_path.parent / "openvoice_se.pth"
            if emb_path.is_file():
                target_se = torch.load(str(emb_path), map_location=device)
            else:
                target_se, _ = se_extractor.get_se(
                    str(request.target_reference_audio_path), self._converter, vad=False
                )
                torch.save(target_se, str(emb_path))

            src_se, _ = se_extractor.get_se(
                str(request.source_audio_path), self._converter, vad=False
            )
            request.output_path.parent.mkdir(parents=True, exist_ok=True)
            self._converter.convert(
                audio_src_path=str(request.source_audio_path),
                src_se=src_se,
                tgt_se=target_se,
                output_path=str(request.output_path),
            )
            insp = inspect_wav(request.output_path)
            return insp.duration_seconds, insp.sample_rate_hz
        except Exception as exc:
            raise EngineError(f"OpenVoice v2 audio conversion failed: {exc}") from exc

    def generate(self, request: GenerationRequest) -> GenerationResult:
        raise EngineError(
            "OpenVoice v2 is an audio-to-audio Voice Converter, not a standalone Text-to-Speech "
            "engine. Use POST /api/v1/conversions with a source audio file, or choose a reference "
            "voice cloning engine (f5_tts_urdu, qwen3_tts_en) for text-to-speech."
        )
