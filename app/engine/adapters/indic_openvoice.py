"""Commercially permissive default speech engine: Indic Parler-TTS (Apache-2.0) + OpenVoice v2 (MIT).

Architecture:
  Stage 1: ai4bharat/indic-parler-tts (Apache-2.0) synthesizes Urdu and English speech spans.
  Stage 2: myshell-ai/OpenVoiceV2 Tone Color Converter (MIT) transfers the user's voice timbre
           extracted from their prepared local reference WAV segment.
  Mixed:   Deterministic Urdu/English script segmentation synthesizes each span cleanly and
           stitches segments with smooth cross-fades.

Offline & Privacy Guarantees:
  - Heavy ML imports are lazy so the backend starts cleanly without PyTorch installed.
  - Inference loads strictly from VOICECITY_MODEL_DIR (local_files_only=True).
  - Never reports ready=True unless both Python runtimes AND local model weights are verified.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import time
from typing import Any

from app.audio.service import inspect_wav, stitch_wav_segments
from app.engine.base import (
    EngineCapability,
    EngineError,
    EngineUnavailableError,
    GenerationRequest,
    GenerationResult,
    UnsupportedLanguageError,
    VoicePreparationResult,
)
from app.text.segmenter import analyze_and_segment

EXPRESSION_PROMPTS: dict[str, str] = {
    "neutral": "A clear, natural speaker delivers the speech at a steady, balanced pace with crisp studio audio quality.",
    "clear": "An articulate speaker speaks clearly with crisp enunciation, balanced pacing, and zero background noise.",
    "warm": "A warm, friendly conversational speaker speaks naturally with smooth intonation and clean studio acoustics.",
    "calm": "A calm, composed narrator speaks smoothly at a relaxed pace with clean, close-microphone audio quality.",
}


class IndicParlerOpenVoiceEngine:
    def __init__(self, model_dir: Path) -> None:
        self.model_dir = model_dir.resolve()
        self._parler_dir = self.model_dir / "indic_parler_tts"
        self._openvoice_dir = self.model_dir / "openvoice_v2" / "converter"
        self._loaded_device: str | None = None
        self._parler_model: Any = None
        self._parler_tokenizer: Any = None
        self._desc_tokenizer: Any = None
        self._converter: Any = None

    @property
    def engine_id(self) -> str:
        return "indic_parler_openvoice"

    def _missing_modules(self) -> list[str]:
        required = ("torch", "transformers", "parler_tts", "openvoice", "soundfile")
        return [m for m in required if importlib.util.find_spec(m) is None]

    def _weights_present(self) -> tuple[bool, list[str]]:
        missing: list[str] = []
        if not (self._parler_dir / "config.json").is_file():
            missing.append(f"Indic Parler-TTS weights ({self._parler_dir})")
        if not (self._openvoice_dir / "checkpoint.pth").is_file():
            missing.append(f"OpenVoice v2 converter checkpoint ({self._openvoice_dir})")
        if not (self._openvoice_dir / "config.json").is_file():
            missing.append(f"OpenVoice v2 converter config ({self._openvoice_dir})")
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
        return {"ur", "en", "mixed"}

    def capabilities(self) -> EngineCapability:
        missing_mods = self._missing_modules()
        weights_ok, missing_weights = self._weights_present()
        installed = len(missing_mods) == 0
        ready = installed and weights_ok
        missing_all = [f"Python module: {m}" for m in missing_mods] + missing_weights

        if ready:
            status_msg = (
                "Local Apache-2.0 / MIT speech pipeline is installed and cached offline. "
                "Human listening review on your Linux Mint laptop is still required to confirm "
                "Pakistani Urdu quality."
            )
        elif not installed:
            status_msg = (
                "Runtime dependencies are not installed on this machine. Run "
                "'bash scripts/install_linux_mint.sh --with-engine indic_parler_openvoice' "
                "on your Linux Mint laptop."
            )
        else:
            status_msg = (
                "Python runtime is installed, but local model weights are missing. Run "
                "'python scripts/download_models.py --engine indic_parler_openvoice' "
                "to cache weights locally for offline use."
            )

        return EngineCapability(
            engine_id=self.engine_id,
            display_name="Indic Parler-TTS + OpenVoice v2 (Commercial Default)",
            version="1.0.0",
            distributable_default=True,
            code_license="Apache-2.0 (parler-tts, transformers) + MIT (OpenVoice)",
            weight_license="Apache-2.0 (ai4bharat/indic-parler-tts) + MIT (myshell-ai/OpenVoiceV2)",
            commercial_compatible=True,
            commercial_note="Permissive Apache-2.0 + MIT for both code and model weights.",
            installed=installed,
            ready=ready,
            offline_supported=True,
            supported_languages=["ur", "en", "mixed"],
            device=self._detect_device("auto"),
            estimated_download_gb=4.2,
            local_weights_present=weights_ok,
            status_message=status_msg,
            source_url="https://huggingface.co/ai4bharat/indic-parler-tts",
            missing_requirements=missing_all,
        )

    def _ensure_loaded(self, preferred_device: str = "auto") -> str:
        cap = self.capabilities()
        if not cap.ready:
            raise EngineUnavailableError(
                f"{cap.status_message} Missing: {', '.join(cap.missing_requirements)}"
            )

        device = self._detect_device(preferred_device)
        if self._parler_model is not None and self._loaded_device == device:
            return device

        try:
            from openvoice.api import ToneColorConverter
            from parler_tts import ParlerTTSForConditionalGeneration
            import torch
            from transformers import AutoTokenizer

            dtype = torch.float16 if device == "cuda" else torch.float32
            self._parler_model = ParlerTTSForConditionalGeneration.from_pretrained(
                str(self._parler_dir),
                local_files_only=True,
                torch_dtype=dtype,
            ).to(device)
            self._parler_tokenizer = AutoTokenizer.from_pretrained(
                str(self._parler_dir),
                local_files_only=True,
            )
            desc_name = getattr(
                self._parler_model.config.text_encoder,
                "_name_or_path",
                str(self._parler_dir),
            )
            try:
                self._desc_tokenizer = AutoTokenizer.from_pretrained(
                    str(self._parler_dir),
                    local_files_only=True,
                )
            except Exception:
                self._desc_tokenizer = AutoTokenizer.from_pretrained(
                    desc_name,
                    local_files_only=True,
                )

            converter = ToneColorConverter(
                str(self._openvoice_dir / "config.json"),
                device=device,
            )
            converter.load_ckpt(str(self._openvoice_dir / "checkpoint.pth"))
            self._converter = converter
            self._loaded_device = device
            return device
        except Exception as exc:
            raise EngineError(f"Failed to load local Indic Parler + OpenVoice models: {exc}") from exc

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
                str(reference_audio_path),
                self._converter,
                vad=False,
            )
            torch.save(target_se, str(emb_path))
            return VoicePreparationResult(
                voice_profile_id=voice_profile_id,
                reference_audio_path=reference_audio_path,
                ready=True,
                embedding_path=emb_path,
                notes="Extracted local OpenVoice v2 speaker tone-color embedding.",
            )
        except Exception as exc:
            raise EngineError(f"OpenVoice speaker embedding extraction failed: {exc}") from exc

    def _synthesize_base_segment(
        self,
        text: str,
        expression: str,
        out_wav: Path,
        device: str,
    ) -> None:
        import soundfile as sf
        import torch

        desc = EXPRESSION_PROMPTS.get(expression, EXPRESSION_PROMPTS["neutral"])
        desc_inputs = self._desc_tokenizer(desc, return_tensors="pt").to(device)
        prompt_inputs = self._parler_tokenizer(text, return_tensors="pt").to(device)

        with torch.no_grad():
            generation = self._parler_model.generate(
                input_ids=desc_inputs.input_ids,
                attention_mask=desc_inputs.attention_mask,
                prompt_input_ids=prompt_inputs.input_ids,
                prompt_attention_mask=prompt_inputs.attention_mask,
            )
        audio_arr = generation.cpu().numpy().squeeze()
        sf.write(str(out_wav), audio_arr, self._parler_model.config.sampling_rate)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if request.language not in self.supported_languages():
            raise UnsupportedLanguageError(
                f"Language '{request.language}' is not supported by {self.engine_id}."
            )

        t0 = time.perf_counter()
        device = self._ensure_loaded(request.compute_device)
        analysis = analyze_and_segment(request.text, requested_language=request.language)  # type: ignore[arg-type]
        if not analysis.segments:
            raise EngineError("No synthesizable text segments found after normalization.")

        import torch
        from openvoice import se_extractor

        emb_path = request.reference_audio_path.parent / "openvoice_se.pth"
        if emb_path.is_file():
            target_se = torch.load(str(emb_path), map_location=device)
        else:
            target_se, _ = se_extractor.get_se(
                str(request.reference_audio_path),
                self._converter,
                vad=False,
            )
            torch.save(target_se, str(emb_path))

        cloned_paths: list[Path] = []
        with tempfile.TemporaryDirectory(prefix="vc_gen_") as tmp:
            tmp_dir = Path(tmp)
            for idx, seg in enumerate(analysis.segments):
                base_wav = tmp_dir / f"base_{idx}.wav"
                cloned_wav = tmp_dir / f"cloned_{idx}.wav"
                self._synthesize_base_segment(seg.text, request.expression, base_wav, device)
                src_se, _ = se_extractor.get_se(str(base_wav), self._converter, vad=False)
                self._converter.convert(
                    audio_src_path=str(base_wav),
                    src_se=src_se,
                    tgt_se=target_se,
                    output_path=str(cloned_wav),
                )
                cloned_paths.append(cloned_wav)

            duration, sample_rate = stitch_wav_segments(
                cloned_paths,
                request.output_path,
                target_sample_rate=24000,
            )

        elapsed = round(time.perf_counter() - t0, 3)
        insp = inspect_wav(request.output_path)
        return GenerationResult(
            audio_path=request.output_path,
            duration_seconds=insp.duration_seconds or duration,
            sample_rate_hz=insp.sample_rate_hz or sample_rate,
            model_id="ai4bharat/indic-parler-tts + myshell-ai/OpenVoiceV2",
            generation_time_seconds=elapsed,
            segments=[{"language": s.language, "text": s.text} for s in analysis.segments],
        )
