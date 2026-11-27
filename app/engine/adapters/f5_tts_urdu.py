"""Secondary Urdu direct zero-shot voice cloning adapter: F5-TTS (MIT) + OpenBible Urdu (CC-BY-SA-4.0).

Truthful Language & License Boundaries:
  - Code license: MIT (SWivid/F5-TTS).
  - Weight license: CC-BY-SA-4.0 (multilingual-tts/F5-TTS-OpenBible-Urdu). Commercial use is
    permitted under CC-BY-SA-4.0 with attribution and ShareAlike on modified weights.
  - Language scope: Urdu ('ur') ONLY. The OpenBible Urdu checkpoint uses an Urdu character
    vocabulary and does NOT claim English or mixed-language support.
  - Offline safety: Requires locally cached model_last.pt, vocab.txt, YAML config, and local
    Vocos vocoder. Requires a reference transcript to prevent automatic Whisper ASR downloads.
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
    GenerationRequest,
    GenerationResult,
    UnsupportedLanguageError,
    VoicePreparationResult,
)


class F5TTSUrduEngine:
    def __init__(self, model_dir: Path) -> None:
        self.model_dir = model_dir.resolve()
        self._ckpt_dir = self.model_dir / "f5_tts_urdu"
        self._vocos_dir = self.model_dir / "vocos"
        self._loaded_device: str | None = None
        self._model: Any = None
        self._vocoder: Any = None

    @property
    def engine_id(self) -> str:
        return "f5_tts_urdu"

    def _missing_modules(self) -> list[str]:
        required = ("torch", "torchaudio", "f5_tts", "omegaconf", "hydra", "soundfile")
        return [m for m in required if importlib.util.find_spec(m) is None]

    def _find_yaml_config(self) -> Path | None:
        if not self._ckpt_dir.is_dir():
            return None
        for pattern in ("F5-TTS_OpenBible_Urdu.yaml", "*.yaml", "*.yml"):
            matches = sorted(self._ckpt_dir.glob(pattern))
            if matches:
                return matches[0]
        return None

    def _weights_present(self) -> tuple[bool, list[str]]:
        missing: list[str] = []
        if not (self._ckpt_dir / "model_last.pt").is_file():
            missing.append(f"F5-TTS Urdu checkpoint ({self._ckpt_dir / 'model_last.pt'})")
        if not (self._ckpt_dir / "vocab.txt").is_file():
            missing.append(f"F5-TTS Urdu vocab ({self._ckpt_dir / 'vocab.txt'})")
        if self._find_yaml_config() is None:
            missing.append(f"F5-TTS Urdu YAML config in {self._ckpt_dir}")
        if not (self._vocos_dir / "config.yaml").is_file():
            missing.append(f"Local Vocos vocoder cache ({self._vocos_dir})")
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
        return {"ur"}

    def capabilities(self) -> EngineCapability:
        missing_mods = self._missing_modules()
        weights_ok, missing_weights = self._weights_present()
        installed = len(missing_mods) == 0
        ready = installed and weights_ok
        missing_all = [f"Python module: {m}" for m in missing_mods] + missing_weights

        if ready:
            status_msg = (
                "F5-TTS Urdu direct zero-shot checkpoint is cached locally (Urdu only). "
                "Provide a short reference transcript on your voice profile for strict offline use."
            )
        elif not installed:
            status_msg = (
                "F5-TTS runtime packages are not installed. Run "
                "'bash scripts/setup_poc_env.sh f5_tts_urdu auto' on Linux Mint."
            )
        else:
            status_msg = (
                "F5-TTS runtime is installed, but the 5.37 GB OpenBible Urdu checkpoint or local "
                "Vocos vocoder is missing. Run 'python scripts/download_models.py --engine f5_tts_urdu'."
            )

        return EngineCapability(
            engine_id=self.engine_id,
            display_name="F5-TTS OpenBible Urdu (Direct Zero-Shot · Urdu Only)",
            version="1.0.0",
            distributable_default=False,
            code_license="MIT (SWivid/F5-TTS)",
            weight_license="CC-BY-SA-4.0 (multilingual-tts/F5-TTS-OpenBible-Urdu)",
            commercial_compatible=True,
            commercial_note=(
                "Commercial use permitted under CC-BY-SA-4.0 with attribution and ShareAlike "
                "for modified weights. Base Emilia weights (CC-BY-NC-4.0) are NOT used."
            ),
            installed=installed,
            ready=ready,
            offline_supported=True,
            supported_languages=["ur"],
            device=self._detect_device("auto"),
            estimated_download_gb=5.5,
            local_weights_present=weights_ok,
            status_message=status_msg,
            source_url="https://huggingface.co/multilingual-tts/F5-TTS-OpenBible-Urdu",
            missing_requirements=missing_all,
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

        cfg_path = self._find_yaml_config()
        assert cfg_path is not None
        try:
            from f5_tts.infer.utils_infer import load_model, load_vocoder
            from hydra.utils import get_class
            from omegaconf import OmegaConf

            model_cfg = OmegaConf.load(str(cfg_path))
            model_cls = get_class(f"f5_tts.model.{model_cfg.model.backbone}")
            self._vocoder = load_vocoder(
                vocoder_name="vocos",
                is_local=True,
                local_path=str(self._vocos_dir),
                device=device,
            )
            self._model = load_model(
                model_cls,
                model_cfg.model.arch,
                str(self._ckpt_dir / "model_last.pt"),
                mel_spec_type="vocos",
                vocab_file=str(self._ckpt_dir / "vocab.txt"),
                use_ema=True,
                device=device,
            )
            self._loaded_device = device
            return device
        except Exception as exc:
            raise EngineError(f"Failed to load local F5-TTS Urdu checkpoint: {exc}") from exc

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
                "F5-TTS conditions directly on your prepared 5-10s reference WAV at generation time. "
                "Add the exact spoken transcript to avoid automatic ASR downloads."
            ),
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if request.language not in self.supported_languages():
            raise UnsupportedLanguageError(
                "F5-TTS OpenBible Urdu supports Urdu ('ur') only. Switch to "
                "'indic_parler_openvoice' in Settings for English or Mixed Urdu-English speech."
            )
        if not request.reference_transcript.strip():
            raise EngineError(
                "F5-TTS requires the spoken transcript of your prepared reference segment in strict "
                "offline mode (prevents unexpected Whisper ASR model downloads). Edit the voice "
                "profile in Voice Library to add the reference transcript."
            )

        t0 = time.perf_counter()
        device = self._ensure_loaded(request.compute_device)
        try:
            from f5_tts.infer.utils_infer import infer_process
            import soundfile as sf

            audio_wave, sample_rate, _ = infer_process(
                str(request.reference_audio_path),
                request.reference_transcript.strip(),
                request.text,
                self._model,
                self._vocoder,
                mel_spec_type="vocos",
                speed=request.speed,
                device=device,
            )
            request.output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(request.output_path), audio_wave, sample_rate)
        except Exception as exc:
            raise EngineError(f"F5-TTS Urdu synthesis failed: {exc}") from exc

        elapsed = round(time.perf_counter() - t0, 3)
        insp = inspect_wav(request.output_path)
        return GenerationResult(
            audio_path=request.output_path,
            duration_seconds=insp.duration_seconds,
            sample_rate_hz=insp.sample_rate_hz,
            model_id="multilingual-tts/F5-TTS-OpenBible-Urdu",
            generation_time_seconds=elapsed,
            segments=[{"language": "ur", "text": request.text}],
        )
