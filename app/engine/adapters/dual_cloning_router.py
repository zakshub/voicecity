"""Compositional reference-audio voice cloning router for Urdu, English, and Mixed text.

Routes genuine reference-audio voice cloning cleanly across language-specialist adapters:
- Urdu ('ur') segments     -> f5_tts_urdu  (SWivid/F5-TTS MIT + OpenBible Urdu CC-BY-SA-4.0)
- English ('en') segments  -> qwen3_tts_en (Qwen/Qwen3-TTS-12Hz-0.6B-Base Apache-2.0)
- Mixed ('mixed') text     -> splits contiguous Urdu/English runs and stitches outputs ONLY
                              when BOTH underlying cloning engines are ready.

Honest Partial Availability:
- If only Urdu cloning is installed, reports supported_languages=['ur'] only.
- If only English cloning is installed, reports supported_languages=['en'] only.
- Never disguises standard TTS as voice cloning.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
import time

from app.audio.service import inspect_wav, stitch_wav_segments
from app.engine.adapters.f5_tts_urdu import F5TTSUrduEngine
from app.engine.adapters.qwen3_tts_en import Qwen3TTSEnglishCloningEngine
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
from app.text.segmenter import analyze_and_segment


class DualCloningRouterEngine:
    def __init__(
        self,
        urdu_engine: F5TTSUrduEngine,
        english_engine: Qwen3TTSEnglishCloningEngine,
    ) -> None:
        self._ur = urdu_engine
        self._en = english_engine

    @property
    def engine_id(self) -> str:
        return "dual_cloning_router"

    def health_check(self) -> bool:
        return self.capabilities().ready

    def supported_languages(self) -> set[str]:
        ur_ready = self._ur.capabilities().ready
        en_ready = self._en.capabilities().ready
        langs: set[str] = set()
        if ur_ready:
            langs.add("ur")
        if en_ready:
            langs.add("en")
        if ur_ready and en_ready:
            langs.add("mixed")
        # Before installation, advertise intended routing scope transparently via capabilities()
        return langs

    def capabilities(self) -> EngineCapability:
        u_cap = self._ur.capabilities()
        e_cap = self._en.capabilities()
        ur_ready = u_cap.ready
        en_ready = e_cap.ready
        any_ready = ur_ready or en_ready
        both_ready = ur_ready and en_ready

        active_langs: list[str] = []
        if ur_ready:
            active_langs.append("ur")
        if en_ready:
            active_langs.append("en")
        if both_ready:
            active_langs.append("mixed")

        missing = list(dict.fromkeys(u_cap.missing_requirements + e_cap.missing_requirements))

        if both_ready:
            status_msg = (
                "Both Urdu cloning (F5-TTS OpenBible Urdu) and English cloning (Qwen3-TTS 0.6B-Base) "
                "are cached locally. Mixed Urdu-English routing is available (unverified listening quality)."
            )
        elif ur_ready:
            status_msg = (
                "Partial cloning ready: Urdu voice cloning (F5-TTS Urdu) is READY, but English "
                "cloning (Qwen3-TTS 0.6B-Base) is NOT installed. English and Mixed modes are unavailable."
            )
        elif en_ready:
            status_msg = (
                "Partial cloning ready: English voice cloning (Qwen3-TTS 0.6B-Base) is READY, but "
                "Urdu cloning (F5-TTS Urdu) is NOT installed. Urdu and Mixed modes are unavailable."
            )
        else:
            status_msg = (
                "Neither Urdu cloning (f5_tts_urdu) nor English cloning (qwen3_tts_en) is installed "
                "yet. Install one or both on Linux Mint to enable genuine reference-audio voice cloning."
            )

        return EngineCapability(
            engine_id=self.engine_id,
            display_name="Dual Reference-Audio Cloning Router (F5-TTS Urdu + Qwen3-TTS English)",
            version="1.0.0",
            capability_class="reference_voice_cloning",
            maturity_level="technically_integrated",
            uses_reference_audio=True,
            requires_reference_transcript=True,
            distributable_default=False,
            license_category="share_alike_optional",
            code_license="MIT (F5-TTS) + Apache-2.0 (Qwen3-TTS)",
            weight_license=(
                "CC-BY-SA-4.0 (F5-TTS-OpenBible-Urdu, optional ShareAlike) + "
                "Apache-2.0 (Qwen3-TTS-12Hz-0.6B-Base)"
            ),
            commercial_compatible=True,
            commercial_note=(
                "Mixed license: English component is permissive Apache-2.0; Urdu component carries "
                "CC-BY-SA-4.0 ShareAlike terms on modified weights."
            ),
            installed=u_cap.installed or e_cap.installed,
            ready=any_ready,
            offline_supported=True,
            supported_languages=active_langs if any_ready else ["ur", "en", "mixed"],
            verified_native_languages=["ur", "en"],
            experimental_languages=["mixed"],
            device=u_cap.device if u_cap.device == "cuda" else e_cap.device,
            estimated_download_gb=8.02,
            min_ram_gb=12,
            min_vram_gb=6,
            cpu_feasible="Slow on CPU; GPU (>=6-8 GB VRAM) strongly recommended when loading both models",
            local_weights_present=u_cap.local_weights_present or e_cap.local_weights_present,
            status_message=status_msg,
            source_url="https://github.com/zakshub/voicecity/blob/main/docs/MODEL_EVALUATION.md",
            license_url="https://github.com/zakshub/voicecity/blob/main/docs/MODEL_LICENSING_REGISTER.md",
            verification=VerificationStatus(
                automated_tests_passed=True,
                model_integration_verified=False,
                actual_speech_generated=False,
                human_listening_completed=False,
                commercial_licensing_verified=True,
            ),
            missing_requirements=missing,
            caveats=[
                "Timbre consistency across Urdu (F5-TTS) and English (Qwen3-TTS) segments in Mixed mode is UNVERIFIED until human listening review.",
                "Urdu cloning carries CC-BY-SA-4.0 ShareAlike license terms and requires a reference transcript.",
                "If only one engine is installed, only that language is usable.",
            ],
        )

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
            notes="Both specialist cloning engines condition directly on your prepared reference WAV.",
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if request.language == "ur":
            if not self._ur.capabilities().ready:
                raise EngineUnavailableError(
                    "Urdu voice cloning (f5_tts_urdu) is not installed or missing local weights."
                )
            return self._ur.generate(request)

        if request.language == "en":
            if not self._en.capabilities().ready:
                raise EngineUnavailableError(
                    "English voice cloning (qwen3_tts_en) is not installed or missing local weights."
                )
            return self._en.generate(request)

        if request.language != "mixed":
            raise UnsupportedLanguageError(f"Unsupported language: {request.language}")

        if not (self._ur.capabilities().ready and self._en.capabilities().ready):
            raise EngineUnavailableError(
                "Mixed Urdu-English voice cloning requires BOTH 'f5_tts_urdu' (Urdu) and "
                "'qwen3_tts_en' (English) to be installed and cached locally."
            )

        t0 = time.perf_counter()
        analysis = analyze_and_segment(request.text, requested_language="mixed")
        if not analysis.segments:
            raise EngineError("No synthesizable segments found.")

        seg_paths: list[Path] = []
        total = len(analysis.segments)
        with tempfile.TemporaryDirectory(prefix="vc_dual_") as tmp:
            tmp_dir = Path(tmp)
            for idx, seg in enumerate(analysis.segments):
                if request.cancel_check and request.cancel_check():
                    raise GenerationCancelledError("Mixed generation cancelled.")
                pct = 10 + int((idx / max(1, total)) * 80)
                if request.progress_callback:
                    request.progress_callback(
                        pct,
                        f"Cloning segment {idx + 1}/{total} ({seg.language.upper()})",
                    )
                seg_out = tmp_dir / f"seg_{idx}_{seg.language}.wav"
                sub_req = GenerationRequest(
                    text=seg.text,
                    language=seg.language,
                    voice_profile_id=request.voice_profile_id,
                    reference_audio_path=request.reference_audio_path,
                    output_path=seg_out,
                    speed=request.speed,
                    expression=request.expression,
                    reference_transcript=request.reference_transcript,
                    compute_device=request.compute_device,
                    cancel_check=request.cancel_check,
                )
                engine = self._ur if seg.language == "ur" else self._en
                engine.generate(sub_req)
                seg_paths.append(seg_out)

            if request.progress_callback:
                request.progress_callback(92, "Stitching Urdu + English cloned segments")
            duration, sr = stitch_wav_segments(
                seg_paths, request.output_path, target_sample_rate=24000
            )

        insp = inspect_wav(request.output_path)
        return GenerationResult(
            audio_path=request.output_path,
            duration_seconds=insp.duration_seconds or duration,
            sample_rate_hz=insp.sample_rate_hz or sr,
            model_id="F5-TTS-OpenBible-Urdu (ur) + Qwen3-TTS-0.6B-Base (en)",
            generation_time_seconds=round(time.perf_counter() - t0, 3),
            segments=[{"language": s.language, "text": s.text} for s in analysis.segments],
            capability_used="reference_voice_cloning",
        )
