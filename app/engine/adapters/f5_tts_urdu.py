"""Reference-audio conditioned zero-shot Urdu voice cloning: F5-TTS + OpenBible Urdu.

Capability Class: reference_voice_cloning (Urdu ONLY)
Maturity Level:   technically_integrated (untested on target Linux Mint laptop)
Code License:     MIT (SWivid/F5-TTS)
Weight License:   CC-BY-SA-4.0 (multilingual-tts/F5-TTS-OpenBible-Urdu) — ShareAlike optional.
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
                "F5-TTS OpenBible Urdu reference-audio voice cloning checkpoint is cached locally "
                "(Urdu ONLY). Requires reference transcript for offline mode. Empirically untested "
                "until Pakistani Urdu listening review completes on Linux Mint."
            )
        elif not installed:
            status_msg = (
                "F5-TTS runtime packages are not installed. Run "
                "'bash scripts/install_linux_mint.sh --with-engine f5_tts_urdu --device auto' "
                "on Linux Mint."
            )
        else:
            status_msg = (
                "F5-TTS runtime is installed, but local weights (5.37 GB model_last.pt + local "
                "Vocos) are missing. Run 'python scripts/download_models.py --engine f5_tts_urdu'."
            )

        return EngineCapability(
            engine_id=self.engine_id,
            display_name="F5-TTS OpenBible Urdu (Reference-Audio Voice Cloning · Urdu Only)",
            version="1.0.0",
            capability_class="reference_voice_cloning",
            maturity_level="technically_integrated",
            uses_reference_audio=True,
            requires_reference_transcript=True,
            distributable_default=False,
            license_category="share_alike_optional",
            code_license="MIT (SWivid/F5-TTS)",
            weight_license="CC-BY-SA-4.0 (multilingual-tts/F5-TTS-OpenBible-Urdu); Vocos MIT",
            commercial_compatible=True,
            commercial_note=(
                "Optional ShareAlike model: CC-BY-SA-4.0 permits commercial use ONLY with "
                "attribution and ShareAlike on modified weights. Not bundled as a permissive default."
            ),
            installed=installed,
            ready=ready,
            offline_supported=True,
            supported_languages=["ur"],
            verified_native_languages=["ur"],
            experimental_languages=[],
            device=self._detect_device("auto"),
            estimated_download_gb=5.5,
            min_ram_gb=8,
            min_vram_gb=4,
            cpu_feasible="Slow (unmeasured RTF on target laptop; GPU strongly recommended)",
            local_weights_present=weights_ok,
            status_message=status_msg,
            source_url="https://huggingface.co/multilingual-tts/F5-TTS-OpenBible-Urdu",
            license_url="https://creativecommons.org/licenses/by-sa/4.0/",
            verification=VerificationStatus(
                automated_tests_passed=True,
                model_integration_verified=False,
                actual_speech_generated=False,
                human_listening_completed=False,
                commercial_licensing_verified=True,
            ),
            missing_requirements=missing_all,
            caveats=[
                "Supports Urdu ONLY; does NOT support English or mixed Latin script.",
                "Trained on Open Bible Urdu corpus (~30,600 utterances); modern colloquial Pakistani Urdu accent is unverified.",
                "Requires spoken transcript of your prepared 5-10s reference clip to avoid automatic Whisper downloads.",
                "Weights carry CC-BY-SA-4.0 ShareAlike terms (optional, not permissive Apache/MIT).",
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
                "F5-TTS Urdu conditions directly on your prepared 5-10s reference WAV at "
                "inference time. Enter the exact spoken reference transcript in Voice Library."
            ),
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if request.language not in self.supported_languages():
            raise UnsupportedLanguageError(
                "F5-TTS OpenBible Urdu supports Urdu ('ur') voice cloning only. "
                "Use 'qwen3_tts_en' for English cloning or 'dual_cloning_router' for mixed speech."
            )
        if not request.reference_transcript.strip():
            raise EngineError(
                "F5-TTS Urdu requires the spoken transcript of your prepared reference segment in "
                "offline mode (prevents hidden Whisper ASR downloads). Add the transcript in Voice Library."
            )
        if request.cancel_check and request.cancel_check():
            raise GenerationCancelledError("Generation cancelled before model load.")

        t0 = time.perf_counter()
        if request.progress_callback:
            request.progress_callback(15, "Loading local F5-TTS Urdu checkpoint")
        device = self._ensure_loaded(request.compute_device)

        if request.cancel_check and request.cancel_check():
            raise GenerationCancelledError("Generation cancelled before synthesis.")

        try:
            from f5_tts.infer.utils_infer import infer_process
            import soundfile as sf

            if request.progress_callback:
                request.progress_callback(45, "Synthesizing reference-conditioned Urdu speech")
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
            if request.cancel_check and request.cancel_check():
                raise GenerationCancelledError("Generation cancelled before writing WAV.")
            if request.progress_callback:
                request.progress_callback(90, "Writing local WAV file")
            request.output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(request.output_path), audio_wave, sample_rate)
        except GenerationCancelledError:
            raise
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
            capability_used="reference_voice_cloning",
        )
