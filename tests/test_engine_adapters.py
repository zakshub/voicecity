"""Tests for strictly separated speech engine capability classes, licensing, and pipeline E2E."""

from __future__ import annotations

import math
from pathlib import Path
import struct
import wave

from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.engine.adapters.f5_tts_urdu import F5TTSUrduEngine
from app.engine.adapters.indic_parler_tts import IndicParlerTTSEngine
from app.engine.adapters.openvoice_v2 import OpenVoiceV2ConverterEngine
from app.engine.adapters.qwen3_tts_en import Qwen3TTSEnglishCloningEngine
from app.engine.base import (
    EngineCapability,
    EngineError,
    GenerationRequest,
    GenerationResult,
    UnsupportedLanguageError,
    VerificationStatus,
    VoicePreparationResult,
)
from app.engine.registry import EngineRegistry, build_default_registry
from app.main import create_app
from app.text.segmenter import analyze_and_segment


def _write_wav(path: Path, duration_sec: float = 1.5, rate: int = 24000) -> Path:
    n = int(duration_sec * rate)
    samples = [int(12000 * math.sin(2.0 * math.pi * 260.0 * i / rate)) for i in range(n)]
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack("<" + "h" * n, *samples))
    return path


class _PipelineTestAdapter:
    """Unit-test-only fixture for API/storage/history pipeline verification.

    Explicitly NOT real voice cloning; real listening tests remain marked SKIPPED.
    """

    @property
    def engine_id(self) -> str:
        return "test_pipeline_adapter"

    def health_check(self) -> bool:
        return True

    def supported_languages(self) -> set[str]:
        return {"ur", "en", "mixed"}

    def capabilities(self) -> EngineCapability:
        return EngineCapability(
            engine_id=self.engine_id,
            display_name="Test Pipeline Fixture (Unit Test Only)",
            version="0.0.1-test",
            capability_class="reference_voice_cloning",
            maturity_level="experimental",
            uses_reference_audio=True,
            requires_reference_transcript=False,
            distributable_default=False,
            license_category="none",
            code_license="MIT",
            weight_license="None (synthetic test tone — NOT voice cloning)",
            commercial_compatible=True,
            commercial_note="Unit test fixture only.",
            installed=True,
            ready=True,
            offline_supported=True,
            supported_languages=["ur", "en", "mixed"],
            verified_native_languages=[],
            experimental_languages=["ur", "en", "mixed"],
            device="cpu",
            estimated_download_gb=0.0,
            min_ram_gb=1,
            min_vram_gb=None,
            cpu_feasible="Test fixture",
            local_weights_present=True,
            status_message="Active unit test fixture.",
            source_url="https://github.com/zakshub/voicecity",
            license_url="https://github.com/zakshub/voicecity",
            verification=VerificationStatus(
                automated_tests_passed=True,
                model_integration_verified=False,
                actual_speech_generated=False,
                human_listening_completed=False,
                commercial_licensing_verified=True,
            ),
        )

    def prepare_voice(
        self, voice_profile_id: str, reference_audio_path: Path, work_dir: Path
    ) -> VoicePreparationResult:
        return VoicePreparationResult(
            voice_profile_id=voice_profile_id,
            reference_audio_path=reference_audio_path,
            ready=True,
            notes="Test fixture prepared.",
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        analysis = analyze_and_segment(request.text, requested_language=request.language)  # type: ignore[arg-type]
        _write_wav(request.output_path, duration_sec=1.2, rate=24000)
        return GenerationResult(
            audio_path=request.output_path,
            duration_seconds=1.2,
            sample_rate_hz=24000,
            model_id="test_pipeline_fixture",
            generation_time_seconds=0.01,
            segments=[{"language": s.language, "text": s.text} for s in analysis.segments],
            capability_used="reference_voice_cloning",
        )


def test_registry_strictly_separates_four_capability_classes(tmp_path: Path) -> None:
    cfg = Settings(data_dir=tmp_path / "data", model_dir=tmp_path / "models")
    registry = build_default_registry(cfg)
    caps = {c.engine_id: c for c in registry.list_capabilities()}

    # 1. Standard TTS (NOT voice cloning)
    parler = caps["indic_parler_tts"]
    assert parler.capability_class == "standard_tts"
    assert parler.uses_reference_audio is False
    assert parler.license_category == "permissive_commercial"

    # 2. Voice Conversion (Urdu NOT native to OpenVoice v2)
    ov = caps["openvoice_v2_converter"]
    assert ov.capability_class == "voice_conversion"
    assert "ur" not in ov.verified_native_languages
    assert "ur" in ov.experimental_languages

    # 3. Experimental Cross-Linguistic Conversion (explicitly marked experimental)
    exp = caps["experimental_parler_openvoice"]
    assert exp.capability_class == "cross_linguistic_voice_conversion"
    assert exp.maturity_level == "experimental"
    assert "ur" in exp.experimental_languages
    assert "ur" not in exp.verified_native_languages

    # 4. Reference-Audio Voice Cloning (Urdu = CC-BY-SA-4.0 optional; English = Apache-2.0)
    f5 = caps["f5_tts_urdu"]
    assert f5.capability_class == "reference_voice_cloning"
    assert f5.uses_reference_audio is True
    assert f5.requires_reference_transcript is True
    assert f5.license_category == "share_alike_optional"
    assert f5.supported_languages == ["ur"]

    qwen = caps["qwen3_tts_en"]
    assert qwen.capability_class == "reference_voice_cloning"
    assert qwen.uses_reference_audio is True
    assert qwen.license_category == "permissive_commercial"
    assert qwen.supported_languages == ["en"]

    # None falsely claim empirical verification or live speech generation
    for cap in caps.values():
        assert cap.ready is False
        assert cap.verification.actual_speech_generated is False
        assert cap.verification.human_listening_completed is False


def test_language_and_capability_boundaries_enforced(tmp_path: Path) -> None:
    ref = _write_wav(tmp_path / "ref.wav", duration_sec=6.0)

    # F5-TTS Urdu rejects English
    f5 = F5TTSUrduEngine(model_dir=tmp_path / "models")
    with pytest.raises(UnsupportedLanguageError):
        f5.generate(
            GenerationRequest(
                text="Hello",
                language="en",
                voice_profile_id="vp_1",
                reference_audio_path=ref,
                output_path=tmp_path / "out.wav",
            )
        )

    # Qwen3-TTS English rejects Urdu
    qwen = Qwen3TTSEnglishCloningEngine(model_dir=tmp_path / "models")
    with pytest.raises(UnsupportedLanguageError):
        qwen.generate(
            GenerationRequest(
                text="السلام علیکم",
                language="ur",
                voice_profile_id="vp_1",
                reference_audio_path=ref,
                output_path=tmp_path / "out.wav",
            )
        )

    # OpenVoice v2 rejects standalone TTS generate()
    ov = OpenVoiceV2ConverterEngine(model_dir=tmp_path / "models")
    with pytest.raises(EngineError):
        ov.generate(
            GenerationRequest(
                text="Hello",
                language="en",
                voice_profile_id="vp_1",
                reference_audio_path=ref,
                output_path=tmp_path / "out.wav",
            )
        )

    # Indic Parler-TTS prepare_voice honestly states it does not clone reference audio
    parler = IndicParlerTTSEngine(model_dir=tmp_path / "models")
    prep = parler.prepare_voice("vp_1", ref, tmp_path)
    assert prep.ready is False
    assert "does not clone" in prep.notes.lower()


def test_capabilities_and_model_verify_endpoints(tmp_path: Path) -> None:
    cfg = Settings(data_dir=tmp_path / "data", model_dir=tmp_path / "models")
    client = TestClient(create_app(settings=cfg))

    caps = client.get("/api/v1/capabilities").json()
    assert caps["speech_generation"] is False
    by_type = caps["capabilities_by_type"]
    assert by_type["reference_voice_cloning"]["urdu"] == "not_installed"
    assert by_type["reference_voice_cloning"]["english"] == "not_installed"
    assert by_type["standard_tts"]["urdu"] == "not_installed"
    assert by_type["cross_linguistic_voice_conversion"]["urdu_experimental"] == "experimental_not_installed"

    verify = client.get("/api/v1/models/verify").json()
    assert verify["models"]["f5_tts_urdu"]["complete"] is False
    assert verify["models"]["qwen3_tts_en"]["complete"] is False


def test_end_to_end_generation_history_preview_and_export_pipeline(tmp_path: Path) -> None:
    cfg = Settings(
        environment="test",
        data_dir=tmp_path / "data",
        model_dir=tmp_path / "models",
        tts_provider="test_pipeline_adapter",
    )
    registry = EngineRegistry([_PipelineTestAdapter()])
    client = TestClient(create_app(settings=cfg, engine_registry=registry))

    wav_src = _write_wav(tmp_path / "user_recording.wav", duration_sec=8.0)
    imp = client.post(
        "/api/v1/voices/import",
        data={"display_name": "Zak Voice", "ownership_confirmed": "true"},
        files={"file": ("zak.wav", wav_src.read_bytes(), "audio/wav")},
    )
    assert imp.status_code == 201
    vid = imp.json()["voice"]["id"]

    g_ur = client.post(
        "/api/v1/generations",
        json={
            "voice_profile_id": vid,
            "text": "السلام علیکم، وائس سٹی میں خوش آمدید۔",
            "language": "ur",
        },
    )
    assert g_ur.status_code == 201
    gen_ur = g_ur.json()["generation"]
    assert gen_ur["status"] == "completed"
    assert gen_ur["has_audio"] is True

    g_mix = client.post(
        "/api/v1/generations",
        json={
            "voice_profile_id": vid,
            "text": "آج شام کو ہم نئی application کا demo دیکھیں گے۔",
            "language": "mixed",
        },
    )
    assert g_mix.status_code == 201
    segs = g_mix.json()["generation"]["segments"]
    assert any(s["language"] == "ur" for s in segs)
    assert any(s["language"] == "en" for s in segs)

    gid = gen_ur["id"]
    audio_resp = client.get(f"/api/v1/generations/{gid}/audio?format=wav&download=1")
    assert audio_resp.status_code == 200
    assert audio_resp.content[:4] == b"RIFF"

    del_resp = client.delete(f"/api/v1/generations/{gid}")
    assert del_resp.status_code == 200
    assert client.get(f"/api/v1/generations/{gid}").status_code == 404


@pytest.mark.skip(
    reason=(
        "PENDING_LAPTOP_HARDWARE: Live F5-TTS Urdu, Qwen3-TTS English, and experimental "
        "Indic Parler -> OpenVoice v2 audio generation + human listening review require Linux Mint."
    )
)
def test_live_neural_urdu_and_english_voice_cloning_quality() -> None:
    raise NotImplementedError("Run on Linux Mint after installing runtimes and downloading weights.")
