"""Reference-audio conditioned zero-shot English voice cloning: Qwen3-TTS-12Hz-0.6B-Base.

Capability Class: reference_voice_cloning (English ONLY within VoiceCity; Urdu NOT supported)
Maturity Level:   technically_integrated (untested on target Linux Mint laptop)
Code License:     Apache-2.0 (QwenLM/Qwen3-TTS)
Weight License:   Apache-2.0 (Qwen/Qwen3-TTS-12Hz-0.6B-Base)
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import time
from typing import Any

from app.audio.service import inspect_wav
from app.engine.base import (
    EngineCapability,
    EngineError,
    EngineUnavailableError,
    GenerationCancelledError,
    GenerationRequest,
    GenerationResult,
    UnsupportedLanguageError,
    VerificationStatus,
    VoicePreparationResult,
)


class Qwen3TTSEnglishCloningEngine:
    def __init__(self, model_dir: Path) -> None:
        self.model_dir = model_dir.resolve()
        self._ckpt_dir = self.model_dir / "qwen3_tts_0.6b_base"
        self._loaded_device: str | None = None
        self._model: Any = None

    @property
    def engine_id(self) -> str:
        return "qwen3_tts_en"

    def _missing_modules(self) -> list[str]:
        required = ("torch", "qwen_tts", "soundfile")
        return [m for m in required if importlib.util.find_spec(m) is None]

    def _weights_present(self) -> tuple[bool, list[str]]:
        missing: list[str] = []
        if not (self._ckpt_dir / "config.json").is_file():
            missing.append(f"Qwen3-TTS-0.6B-Base weights ({self._ckpt_dir})")
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
                "Qwen3-TTS 0.6B-Base (Apache-2.0) is cached locally for reference-audio English "
                "voice cloning. Urdu is NOT supported by Qwen3-TTS base weights."
            )
        elif not installed:
            status_msg = (
                "Qwen3-TTS runtime packages are not installed. Run "
                "'bash scripts/install_linux_mint.sh --with-engine qwen3_tts_en --device auto' "
                "on Linux Mint."
            )
        else:
            status_msg = (
                "Qwen3-TTS runtime is installed, but local weights (~2.52 GB) are missing. Run "
                "'python scripts/download_models.py --engine qwen3_tts_en'."
            )

        return EngineCapability(
            engine_id=self.engine_id,
            display_name="Qwen3-TTS 0.6B Base (Reference-Audio Voice Cloning · English Only)",
            version="0.6B-Base",
            capability_class="reference_voice_cloning",
            maturity_level="technically_integrated",
            uses_reference_audio=True,
            requires_reference_transcript=False,
            distributable_default=True,
            license_category="permissive_commercial",
            code_license="Apache-2.0 (QwenLM/Qwen3-TTS)",
            weight_license="Apache-2.0 (Qwen/Qwen3-TTS-12Hz-0.6B-Base)",
            commercial_compatible=True,
            commercial_note="Permissive Apache-2.0 for both code and weights (English only; no native Urdu).",
            installed=installed,
            ready=ready,
            offline_supported=True,
            supported_languages=["en"],
            verified_native_languages=["en"],
            experimental_languages=[],
            device=self._detect_device("auto"),
            estimated_download_gb=2.52,
            min_ram_gb=8,
            min_vram_gb=4,
            cpu_feasible="Possible on CPU (slow; ~4-6 GB GPU VRAM recommended)",
            local_weights_present=weights_ok,
            status_message=status_msg,
            source_url="https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            license_url="https://github.com/QwenLM/Qwen3-TTS/blob/main/LICENSE",
            verification=VerificationStatus(
                automated_tests_passed=True,
                model_integration_verified=False,
                actual_speech_generated=False,
                human_listening_completed=False,
                commercial_licensing_verified=True,
            ),
            missing_requirements=missing_all,
            caveats=[
                "Officially supports 10 languages (EN, ZH, JA, KO, DE, FR, RU, PT, ES, IT) — Urdu is NOT supported.",
                "Conditions directly on a 3-10s reference WAV clip (x-vector mode works without transcript; adding reference transcript improves cloning fidelity).",
                "Hardware latency and speaker similarity on your Linux Mint laptop remain untested.",
            ],
        )

    def _ensure_loaded(self, preferred_device: str = "auto") -> str:
        cap = self.capabilities()
        if not cap.ready:
            raise EngineUnavailableError(
                f"{cap.status_message} Missing: {', '.join(cap.missing_requirements)}"
            )
        device = self._detect_device(preferred_device)
        if self._model is not None and self._loaded_device == device:
            return device
        try:
            from qwen_tts import Qwen3TTSModel
            import torch

            dtype = torch.bfloat16 if device == "cuda" else torch.float32
            self._model = Qwen3TTSModel.from_pretrained(
                str(self._ckpt_dir),
                device_map=device,
                dtype=dtype,
                local_files_only=True,
            )
            self._loaded_device = device
            return device
        except Exception as exc:
            raise EngineError(f"Failed to load local Qwen3-TTS model: {exc}") from exc

    def prepare_voice(
        self,
        voice_profile_id: str,
        reference_audio_path: Path,
        work_dir: Path,
    ) -> VoicePreparationResult:
        cap = self.capabilities()
        return VoicePreparationResult(
            voice_profile_id=voice_profile_id,
            reference_audio_path=reference_audio_path,
            ready=cap.ready,
            notes=(
                "Qwen3-TTS 0.6B-Base conditions directly on your prepared 3-10s reference WAV "
                "for English zero-shot voice cloning."
            ),
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if request.language not in self.supported_languages():
            raise UnsupportedLanguageError(
                "Qwen3-TTS Base supports English ('en') voice cloning only — Urdu is not in its "
                "official 10-language set. Use 'f5_tts_urdu' for Urdu cloning or "
                "'dual_cloning_router' when both Urdu and English engines are installed."
            )
        if request.cancel_check and request.cancel_check():
            raise GenerationCancelledError("Generation cancelled before model load.")

        t0 = time.perf_counter()
        if request.progress_callback:
            request.progress_callback(15, "Loading local Qwen3-TTS English cloning model")
        self._ensure_loaded(request.compute_device)

        if request.cancel_check and request.cancel_check():
            raise GenerationCancelledError("Generation cancelled before synthesis.")

        try:
            import soundfile as sf

            if request.progress_callback:
                request.progress_callback(50, "Synthesizing reference-conditioned English speech")
            ref_txt = request.reference_transcript.strip()
            wavs, sr = self._model.generate_voice_clone(
                text=request.text,
                language="English",
                ref_audio=str(request.reference_audio_path),
                ref_text=ref_txt if ref_txt else None,
                x_vector_only_mode=not bool(ref_txt),
            )
            if request.cancel_check and request.cancel_check():
                raise GenerationCancelledError("Generation cancelled before writing WAV.")
            if request.progress_callback:
                request.progress_callback(90, "Writing local WAV file")
            request.output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(request.output_path), wavs[0], sr)
        except GenerationCancelledError:
            raise
        except Exception as exc:
            raise EngineError(f"Qwen3-TTS English voice cloning failed: {exc}") from exc

        elapsed = round(time.perf_counter() - t0, 3)
        insp = inspect_wav(request.output_path)
        return GenerationResult(
            audio_path=request.output_path,
            duration_seconds=insp.duration_seconds,
            sample_rate_hz=insp.sample_rate_hz,
            model_id="Qwen/Qwen3-TTS-12Hz-0.6B-Base",
            generation_time_seconds=elapsed,
            segments=[{"language": "en", "text": request.text}],
            capability_used="reference_voice_cloning",
        )
