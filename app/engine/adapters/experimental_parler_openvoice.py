"""EXPERIMENTAL cross-linguistic voice conversion: Indic Parler-TTS -> OpenVoice v2.

HONEST DISCLOSURE:
- Capability Class: cross_linguistic_voice_conversion (NOT native Urdu voice cloning!)
- Maturity Level:   experimental (unverified on Urdu!)
- Indic Parler-TTS is standard synthetic TTS (no voice cloning).
- OpenVoice v2 does NOT include Urdu in its 6 documented native V2 languages (EN/ES/FR/ZH/JA/KO).
- Piping Indic Parler Urdu audio into OpenVoice v2 is an EXPERIMENTAL cross-linguistic voice
  conversion experiment that requires empirical Pakistani Urdu listening evaluation on Linux Mint.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
import time

from app.audio.service import inspect_wav, stitch_wav_segments
from app.engine.adapters.indic_parler_tts import IndicParlerTTSEngine
from app.engine.adapters.openvoice_v2 import OpenVoiceV2ConverterEngine
from app.engine.base import (
    EngineCapability,
    EngineError,
    EngineUnavailableError,
    GenerationCancelledError,
    GenerationRequest,
    GenerationResult,
    UnsupportedLanguageError,
    VerificationStatus,
    VoiceConversionRequest,
    VoicePreparationResult,
)
from app.text.segmenter import analyze_and_segment


class ExperimentalParlerOpenVoiceEngine:
    def __init__(
        self,
        parler_engine: IndicParlerTTSEngine,
        openvoice_engine: OpenVoiceV2ConverterEngine,
    ) -> None:
        self._parler = parler_engine
        self._openvoice = openvoice_engine

    @property
    def engine_id(self) -> str:
        return "experimental_parler_openvoice"

    def health_check(self) -> bool:
        return self.capabilities().ready

    def supported_languages(self) -> set[str]:
        return {"ur", "en", "mixed"}

    def capabilities(self) -> EngineCapability:
        p_cap = self._parler.capabilities()
        o_cap = self._openvoice.capabilities()
        installed = p_cap.installed and o_cap.installed
        weights_ok = p_cap.local_weights_present and o_cap.local_weights_present
        ready = p_cap.ready and o_cap.ready
        missing = list(dict.fromkeys(p_cap.missing_requirements + o_cap.missing_requirements))

        if ready:
            status_msg = (
                "EXPERIMENTAL cross-linguistic conversion pipeline ready (Indic Parler-TTS -> "
                "OpenVoice v2). WARNING: Urdu is NOT a documented native OpenVoice v2 language; "
                "treat output as experimental pending human listening evaluation."
            )
        else:
            status_msg = (
                "EXPERIMENTAL cross-linguistic pipeline not installed. Requires both "
                "Indic Parler-TTS (Standard TTS) and OpenVoice v2 (Voice Converter)."
            )

        return EngineCapability(
            engine_id=self.engine_id,
            display_name="EXPERIMENTAL: Indic Parler-TTS -> OpenVoice v2 (Cross-Linguistic Conversion)",
            version="0.1.0-experimental",
            capability_class="cross_linguistic_voice_conversion",
            maturity_level="experimental",
            uses_reference_audio=True,
            requires_reference_transcript=False,
            distributable_default=False,
            license_category="permissive_commercial",
            code_license="Apache-2.0 (parler-tts) + MIT (OpenVoice)",
            weight_license="Apache-2.0 (ai4bharat/indic-parler-tts) + MIT (myshell-ai/OpenVoiceV2)",
            commercial_compatible=True,
            commercial_note=(
                "Permissive Apache-2.0 + MIT licenses, BUT technically EXPERIMENTAL for Urdu "
                "because OpenVoice v2 does not natively list Urdu."
            ),
            installed=installed,
            ready=ready,
            offline_supported=True,
            supported_languages=["ur", "en", "mixed"],
            verified_native_languages=["en"],
            experimental_languages=["ur", "mixed"],
            device=p_cap.device,
            estimated_download_gb=4.14,
            min_ram_gb=8,
            min_vram_gb=5,
            cpu_feasible="Very slow on CPU (two neural stages); GPU strongly recommended",
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
            missing_requirements=missing,
            caveats=[
                "EXPERIMENTAL ONLY — NOT verified native Urdu voice cloning.",
                "Stage 1 (Indic Parler-TTS) is standard TTS without voice cloning.",
                "Stage 2 (OpenVoice v2) does NOT include Urdu in its documented native V2 languages.",
                "Voice timbre consistency and Pakistani Urdu prosody after conversion are unverified.",
            ],
        )

    def prepare_voice(
        self,
        voice_profile_id: str,
        reference_audio_path: Path,
        work_dir: Path,
    ) -> VoicePreparationResult:
        return self._openvoice.prepare_voice(voice_profile_id, reference_audio_path, work_dir)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if request.language not in self.supported_languages():
            raise UnsupportedLanguageError(
                f"Language '{request.language}' is unsupported by {self.engine_id}."
            )
        if not self.capabilities().ready:
            raise EngineUnavailableError(self.capabilities().status_message)
        if request.cancel_check and request.cancel_check():
            raise GenerationCancelledError("Generation cancelled before start.")

        t0 = time.perf_counter()
        analysis = analyze_and_segment(request.text, requested_language=request.language)  # type: ignore[arg-type]
        if not analysis.segments:
            raise EngineError("No synthesizable text segments found.")

        converted_paths: list[Path] = []
        total_segs = len(analysis.segments)
        with tempfile.TemporaryDirectory(prefix="vc_exp_") as tmp:
            tmp_dir = Path(tmp)
            for idx, seg in enumerate(analysis.segments):
                if request.cancel_check and request.cancel_check():
                    raise GenerationCancelledError("Generation cancelled during synthesis.")
                pct_base = 10 + int((idx / max(1, total_segs)) * 75)
                if request.progress_callback:
                    request.progress_callback(
                        pct_base,
                        f"Stage 1/2 (Segment {idx + 1}/{total_segs}): Standard TTS ({seg.language.upper()})",
                    )
                base_wav = tmp_dir / f"base_{idx}.wav"
                conv_wav = tmp_dir / f"conv_{idx}.wav"
                self._parler.synthesize_to_wav(
                    text=seg.text,
                    output_path=base_wav,
                    expression=request.expression,
                    compute_device=request.compute_device,
                )
                if request.progress_callback:
                    request.progress_callback(
                        min(88, pct_base + 15),
                        f"Stage 2/2 (Segment {idx + 1}/{total_segs}): Experimental OpenVoice v2 conversion",
                    )
                self._openvoice.convert_audio(
                    VoiceConversionRequest(
                        source_audio_path=base_wav,
                        target_reference_audio_path=request.reference_audio_path,
                        output_path=conv_wav,
                        voice_profile_id=request.voice_profile_id,
                        compute_device=request.compute_device,
                    )
                )
                converted_paths.append(conv_wav)

            if request.progress_callback:
                request.progress_callback(92, "Stitching converted audio segments")
            duration, sr = stitch_wav_segments(
                converted_paths, request.output_path, target_sample_rate=24000
            )

        insp = inspect_wav(request.output_path)
        return GenerationResult(
            audio_path=request.output_path,
            duration_seconds=insp.duration_seconds or duration,
            sample_rate_hz=insp.sample_rate_hz or sr,
            model_id="EXPERIMENTAL: ai4bharat/indic-parler-tts -> myshell-ai/OpenVoiceV2",
            generation_time_seconds=round(time.perf_counter() - t0, 3),
            segments=[{"language": s.language, "text": s.text} for s in analysis.segments],
            capability_used="cross_linguistic_voice_conversion",
        )
