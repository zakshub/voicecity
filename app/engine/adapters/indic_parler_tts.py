"""Standard multilingual Text-to-Speech ONLY: AI4Bharat Indic Parler-TTS (Apache-2.0).

IMPORTANT HONEST BOUNDARY:
- Capability Class: standard_tts (NOT voice cloning!)
- Uses text voice-style descriptions; DOES NOT clone a user's voice from a reference WAV.
- Supports Urdu ('ur') and English ('en') synthetic speaker generation.
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

EXPRESSION_PROMPTS: dict[str, str] = {
    "neutral": "A clear, natural speaker delivers speech at a steady, balanced pace with crisp studio audio.",
    "clear": "An articulate speaker speaks clearly with crisp enunciation and zero background noise.",
    "warm": "A warm, friendly conversational speaker speaks naturally with smooth intonation.",
    "calm": "A calm narrator speaks smoothly at a relaxed pace with clean close-microphone audio.",
}


class IndicParlerTTSEngine:
    def __init__(self, model_dir: Path) -> None:
        self.model_dir = model_dir.resolve()
        self._parler_dir = self.model_dir / "indic_parler_tts"
        self._loaded_device: str | None = None
        self._model: Any = None
        self._prompt_tokenizer: Any = None
        self._desc_tokenizer: Any = None

    @property
    def engine_id(self) -> str:
        return "indic_parler_tts"

    def _missing_modules(self) -> list[str]:
        required = ("torch", "transformers", "parler_tts", "soundfile")
        return [m for m in required if importlib.util.find_spec(m) is None]

    def _weights_present(self) -> tuple[bool, list[str]]:
        missing: list[str] = []
        if not (self._parler_dir / "config.json").is_file():
            missing.append(f"Indic Parler-TTS weights ({self._parler_dir})")
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
        return {"ur", "en"}

    def capabilities(self) -> EngineCapability:
        missing_mods = self._missing_modules()
        weights_ok, missing_weights = self._weights_present()
        installed = len(missing_mods) == 0
        ready = installed and weights_ok
        missing_all = [f"Python module: {m}" for m in missing_mods] + missing_weights

        if ready:
            status_msg = (
                "Indic Parler-TTS (Apache-2.0) is cached locally for STANDARD TEXT-TO-SPEECH only "
                "(synthetic speaker). It does NOT clone your personal voice from a WAV recording."
            )
        elif not installed:
            status_msg = (
                "Indic Parler-TTS runtime is not installed. Run "
                "'bash scripts/install_linux_mint.sh --with-engine indic_parler_tts --device auto'."
            )
        else:
            status_msg = (
                "Indic Parler-TTS runtime is installed, but weights (~4.0 GB) are missing. Run "
                "'python scripts/download_models.py --engine indic_parler_tts'."
            )

        return EngineCapability(
            engine_id=self.engine_id,
            display_name="AI4Bharat Indic Parler-TTS (Standard TTS ONLY · Not Voice Cloning)",
            version="1.0.0",
            capability_class="standard_tts",
            maturity_level="technically_integrated",
            uses_reference_audio=False,
            requires_reference_transcript=False,
            distributable_default=False,
            license_category="permissive_commercial",
            code_license="Apache-2.0 (huggingface/parler-tts)",
            weight_license="Apache-2.0 (ai4bharat/indic-parler-tts)",
            commercial_compatible=True,
            commercial_note="Permissive Apache-2.0 code & weights — Standard TTS ONLY (no reference voice cloning).",
            installed=installed,
            ready=ready,
            offline_supported=True,
            supported_languages=["ur", "en"],
            verified_native_languages=["ur", "en"],
            experimental_languages=[],
            device=self._detect_device("auto"),
            estimated_download_gb=4.0,
            min_ram_gb=8,
            min_vram_gb=4,
            cpu_feasible="Slow on CPU (940M autoregressive params; >=4-5 GB GPU VRAM recommended)",
            local_weights_present=weights_ok,
            status_message=status_msg,
            source_url="https://huggingface.co/ai4bharat/indic-parler-tts",
            license_url="https://huggingface.co/ai4bharat/indic-parler-tts",
            verification=VerificationStatus(
                automated_tests_passed=True,
                model_integration_verified=False,
                actual_speech_generated=False,
                human_listening_completed=False,
                commercial_licensing_verified=True,
            ),
            missing_requirements=missing_all,
            caveats=[
                "NOT a voice cloning model: ignores your uploaded reference WAV and synthesizes a prompt-described speaker.",
                "Useful only as standalone Urdu/English TTS or as Stage 1 feeding an explicit voice converter.",
                "Pakistani Urdu accent naturalness has not yet been evaluated on target laptop hardware.",
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
            from parler_tts import ParlerTTSForConditionalGeneration
            import torch
            from transformers import AutoTokenizer

            dtype = torch.float16 if device == "cuda" else torch.float32
            self._model = ParlerTTSForConditionalGeneration.from_pretrained(
                str(self._parler_dir),
                local_files_only=True,
                torch_dtype=dtype,
            ).to(device)
            self._prompt_tokenizer = AutoTokenizer.from_pretrained(
                str(self._parler_dir),
                local_files_only=True,
            )
            self._desc_tokenizer = AutoTokenizer.from_pretrained(
                str(self._parler_dir),
                local_files_only=True,
            )
            self._loaded_device = device
            return device
        except Exception as exc:
            raise EngineError(f"Failed to load local Indic Parler-TTS model: {exc}") from exc

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
            notes=(
                "Indic Parler-TTS is Standard TTS and does NOT clone reference audio recordings."
            ),
        )

    def synthesize_to_wav(
        self,
        text: str,
        output_path: Path,
        expression: str = "neutral",
        compute_device: str = "auto",
    ) -> tuple[float, int]:
        device = self._ensure_loaded(compute_device)
        import soundfile as sf
        import torch

        desc = EXPRESSION_PROMPTS.get(expression, EXPRESSION_PROMPTS["neutral"])
        desc_inputs = self._desc_tokenizer(desc, return_tensors="pt").to(device)
        prompt_inputs = self._prompt_tokenizer(text, return_tensors="pt").to(device)
        with torch.no_grad():
            generation = self._model.generate(
                input_ids=desc_inputs.input_ids,
                attention_mask=desc_inputs.attention_mask,
                prompt_input_ids=prompt_inputs.input_ids,
                prompt_attention_mask=prompt_inputs.attention_mask,
            )
        audio_arr = generation.cpu().numpy().squeeze()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), audio_arr, self._model.config.sampling_rate)
        insp = inspect_wav(output_path)
        return insp.duration_seconds, insp.sample_rate_hz

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if request.language not in self.supported_languages():
            raise UnsupportedLanguageError(
                f"Indic Parler-TTS supports standard TTS for {sorted(self.supported_languages())}."
            )
        if request.cancel_check and request.cancel_check():
            raise GenerationCancelledError("Generation cancelled before synthesis.")

        t0 = time.perf_counter()
        if request.progress_callback:
            request.progress_callback(25, "Synthesizing standard TTS (non-cloned synthetic voice)")
        duration, sr = self.synthesize_to_wav(
            text=request.text,
            output_path=request.output_path,
            expression=request.expression,
            compute_device=request.compute_device,
        )
        return GenerationResult(
            audio_path=request.output_path,
            duration_seconds=duration,
            sample_rate_hz=sr,
            model_id="ai4bharat/indic-parler-tts (Standard TTS — NOT cloned)",
            generation_time_seconds=round(time.perf_counter() - t0, 3),
            segments=[{"language": request.language, "text": request.text}],
            capability_used="standard_tts",
        )
