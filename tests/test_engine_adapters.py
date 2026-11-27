"""Milestone 4 tests: engine registry, license metadata, truthful readiness, and pipeline E2E."""

from __future__ import annotations

import math
from pathlib import Path
import struct
import wave

from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.engine.adapters.f5_tts_urdu import F5TTSUrduEngine
from app.engine.adapters.indic_openvoice import IndicParlerOpenVoiceEngine
from app.engine.base import (
    EngineCapability,
    GenerationRequest,
    GenerationResult,
    UnsupportedLanguageError,
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
    """Test-only deterministic WAV adapter to verify generation API, storage, and history wiring.

    Does NOT represent real neural speech quality. Real model audio tests remain marked PENDING.
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
            display_name="Test Pipeline Adapter (Unit Test Only)",
            version="0.0.1-test",
            distributable_default=True,
            code_license="MIT",
            weight_license="None (synthetic test tone)",
            commercial_compatible=True,
            commercial_note="Test fixture only.",
            installed=True,
            ready=True,
            offline_supported=True,
            supported_languages=["ur", "en", "mixed"],
            device="cpu",
            estimated_download_gb=0.0,
            local_weights_present=True,
            status_message="Active test fixture.",
            source_url="https://github.com/zakshub/voicecity",
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
        )


def test_default_registry_loads_commercially_compatible_adapters(tmp_path: Path) -> None:
    cfg = Settings(data_dir=tmp_path / "data", model_dir=tmp_path / "models")
    registry = build_default_registry(cfg)
    ids = registry.list_ids()
    assert "indic_parler_openvoice" in ids
    assert "f5_tts_urdu" in ids

    default_eng = registry.resolve(None)
    assert default_eng.engine_id == "indic_parler_openvoice"
    cap = default_eng.capabilities()
    assert cap.distributable_default is True
    assert cap.commercial_compatible is True
    assert "Apache-2.0" in cap.weight_license
    assert "MIT" in cap.weight_license
    assert cap.ready is False  # Truthful: weights are not cached in tmp_path


def test_f5_tts_urdu_enforces_urdu_only_language_boundary(tmp_path: Path) -> None:
    eng = F5TTSUrduEngine(model_dir=tmp_path / "models")
    assert eng.supported_languages() == {"ur"}
    cap = eng.capabilities()
    assert "CC-BY-SA-4.0" in cap.weight_license
    assert cap.ready is False

    ref = _write_wav(tmp_path / "ref.wav", duration_sec=6.0)
    with pytest.raises(UnsupportedLanguageError):
        eng.generate(
            GenerationRequest(
                text="Hello world",
                language="en",
                voice_profile_id="vp_test",
                reference_audio_path=ref,
                output_path=tmp_path / "out.wav",
            )
        )


def test_indic_openvoice_rejects_unknown_language(tmp_path: Path) -> None:
    eng = IndicParlerOpenVoiceEngine(model_dir=tmp_path / "models")
    assert eng.supported_languages() == {"ur", "en", "mixed"}
    ref = _write_wav(tmp_path / "ref.wav", duration_sec=6.0)
    with pytest.raises(UnsupportedLanguageError):
        eng.generate(
            GenerationRequest(
                text="Bonjour",
                language="fr",
                voice_profile_id="vp_test",
                reference_audio_path=ref,
                output_path=tmp_path / "out.wav",
            )
        )


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

    # 1. Pure Urdu generation
    g_ur = client.post(
        "/api/v1/generations",
        json={
            "voice_profile_id": vid,
            "text": "السلام علیکم، وائس سٹی میں خوش آمدید۔",
            "language": "ur",
            "speed": 1.0,
            "expression": "neutral",
        },
    )
    assert g_ur.status_code == 201
    gen_ur = g_ur.json()["generation"]
    assert gen_ur["status"] == "completed"
    assert gen_ur["has_audio"] is True

    # 2. Pure English generation
    g_en = client.post(
        "/api/v1/generations",
        json={
            "voice_profile_id": vid,
            "text": "Welcome to VoiceCity running locally on Linux.",
            "language": "en",
        },
    )
    assert g_en.status_code == 201

    # 3. Mixed Urdu-English generation
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

    # Preview & WAV download check
    gid = gen_ur["id"]
    audio_resp = client.get(f"/api/v1/generations/{gid}/audio?format=wav&download=1")
    assert audio_resp.status_code == 200
    assert audio_resp.headers["content-type"].startswith("audio/wav")
    assert audio_resp.content[:4] == b"RIFF"

    # History filter check
    hist_mixed = client.get("/api/v1/generations?language=mixed").json()
    assert hist_mixed["count"] == 1

    # Delete generation removes WAV from disk
    del_resp = client.delete(f"/api/v1/generations/{gid}")
    assert del_resp.status_code == 200
    assert client.get(f"/api/v1/generations/{gid}").status_code == 404


@pytest.mark.skip(
    reason=(
        "PENDING_LAPTOP_HARDWARE: Live Pakistani Urdu, English, and mixed-language neural "
        "synthesis + human listening review require the Linux Mint laptop with cached model weights."
    )
)
def test_live_neural_urdu_and_english_voice_cloning_quality() -> None:
    raise NotImplementedError("Run scripts/poc_eval.py on Linux Mint after model download.")
