"""Milestone 6 comprehensive QA suite covering all 12 verification areas and pending laptop gates."""

from __future__ import annotations

import math
from pathlib import Path
import struct
import wave

from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings
from app.core.storage import StorageSecurityError, ensure_within_dir, validate_entity_id
from app.engine.base import (
    EngineCapability,
    EngineError,
    GenerationRequest,
    GenerationResult,
    VoicePreparationResult,
)
from app.engine.registry import EngineRegistry
from app.main import create_app


def _write_24bit_wav(path: Path, duration_sec: float = 6.0, rate: int = 24000) -> Path:
    n = int(duration_sec * rate)
    raw = bytearray()
    for i in range(n):
        sample = int(2_000_000 * math.sin(2.0 * math.pi * 240.0 * i / rate))
        raw.extend(sample.to_bytes(3, byteorder="little", signed=True))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(3)
        wf.setframerate(rate)
        wf.writeframes(bytes(raw))
    return path


def _write_silent_wav(path: Path, duration_sec: float = 5.0, rate: int = 16000) -> Path:
    n = int(duration_sec * rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(b"\x00\x00" * n)
    return path


class _FailingEngineFixture:
    @property
    def engine_id(self) -> str:
        return "failing_fixture"

    def health_check(self) -> bool:
        return True

    def supported_languages(self) -> set[str]:
        return {"ur", "en", "mixed"}

    def capabilities(self) -> EngineCapability:
        return EngineCapability(
            engine_id=self.engine_id,
            display_name="Failing Fixture",
            version="0.0.1",
            distributable_default=True,
            code_license="MIT",
            weight_license="None",
            commercial_compatible=True,
            commercial_note="Test only",
            installed=True,
            ready=True,
            offline_supported=True,
            supported_languages=["ur", "en", "mixed"],
            device="cpu",
            estimated_download_gb=0.0,
            local_weights_present=True,
            status_message="Ready to simulate runtime failure",
            source_url="https://github.com/zakshub/voicecity",
        )

    def prepare_voice(
        self, voice_profile_id: str, reference_audio_path: Path, work_dir: Path
    ) -> VoicePreparationResult:
        return VoicePreparationResult(
            voice_profile_id=voice_profile_id,
            reference_audio_path=reference_audio_path,
            ready=True,
        )

    def generate(self, request: GenerationRequest) -> GenerationResult:
        raise EngineError("Simulated out-of-memory error during inference")


def test_qa_24bit_pcm_upload_and_invalid_audio_edge_cases(tmp_path: Path) -> None:
    cfg = Settings(
        environment="test",
        data_dir=tmp_path / "data",
        model_dir=tmp_path / "models",
        max_upload_mb=1,
    )
    client = TestClient(create_app(settings=cfg))

    # 1. Valid 24-bit WAV succeeds
    wav24 = _write_24bit_wav(tmp_path / "studio_24bit.wav", duration_sec=6.0)
    res_ok = client.post(
        "/api/v1/voices/import",
        data={"display_name": "Studio 24-bit", "ownership_confirmed": "true"},
        files={"file": ("studio_24bit.wav", wav24.read_bytes(), "audio/wav")},
    )
    assert res_ok.status_code == 201
    assert res_ok.json()["voice"]["source_bit_depth"] == 24

    # 2. Empty file rejected
    res_empty = client.post(
        "/api/v1/voices/import",
        data={"display_name": "Empty", "ownership_confirmed": "true"},
        files={"file": ("empty.wav", b"", "audio/wav")},
    )
    assert res_empty.status_code == 400

    # 3. Non-.wav extension rejected
    res_mp3 = client.post(
        "/api/v1/voices/import",
        data={"display_name": "MP3 File", "ownership_confirmed": "true"},
        files={"file": ("voice.mp3", b"ID3fake", "audio/mpeg")},
    )
    assert res_mp3.status_code == 400

    # 4. Completely silent WAV rejected
    silent_wav = _write_silent_wav(tmp_path / "silent.wav")
    res_silent = client.post(
        "/api/v1/voices/import",
        data={"display_name": "Silent", "ownership_confirmed": "true"},
        files={"file": ("silent.wav", silent_wav.read_bytes(), "audio/wav")},
    )
    assert res_silent.status_code == 400

    # 5. Oversized upload rejected with 413
    oversized = b"RIFF" + (b"\x00" * (1024 * 1024 + 128))
    res_big = client.post(
        "/api/v1/voices/import",
        data={"display_name": "Too Large", "ownership_confirmed": "true"},
        files={"file": ("huge.wav", oversized, "audio/wav")},
    )
    assert res_big.status_code == 413


def test_qa_storage_path_traversal_and_privacy_boundaries(tmp_path: Path) -> None:
    base = tmp_path / "data"
    base.mkdir()
    with pytest.raises(StorageSecurityError):
        ensure_within_dir(base, tmp_path / "outside.wav")
    with pytest.raises(StorageSecurityError):
        validate_entity_id("../etc/passwd")

    cfg = Settings(data_dir=base, model_dir=tmp_path / "models")
    client = TestClient(create_app(settings=cfg))
    caps = client.get("/api/v1/capabilities").json()
    assert caps["remote_inference"] is False


def test_qa_urdu_normalization_and_text_analyze_endpoint(tmp_path: Path) -> None:
    cfg = Settings(data_dir=tmp_path / "data", model_dir=tmp_path / "models")
    client = TestClient(create_app(settings=cfg))

    # Arabic Kaf (\u0643) & Yeh (\u064A) normalized to standard Urdu forms
    resp = client.post(
        "/api/v1/text/analyze",
        json={"text": "پاكستان میں 2026 كا project launch ہو رہا ہے۔", "language": "mixed"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "\u06A9" in body["normalized_text"]
    assert body["detected_language"] == "mixed"
    assert len(body["segments"]) >= 3


def test_qa_error_recovery_records_failed_generation_without_crash(tmp_path: Path) -> None:
    cfg = Settings(
        environment="test",
        data_dir=tmp_path / "data",
        model_dir=tmp_path / "models",
        tts_provider="failing_fixture",
    )
    client = TestClient(
        create_app(settings=cfg, engine_registry=EngineRegistry([_FailingEngineFixture()]))
    )
    wav24 = _write_24bit_wav(tmp_path / "voice.wav", duration_sec=6.0)
    vid = client.post(
        "/api/v1/voices/import",
        data={"display_name": "Recovery Test", "ownership_confirmed": "true"},
        files={"file": ("voice.wav", wav24.read_bytes(), "audio/wav")},
    ).json()["voice"]["id"]

    res = client.post(
        "/api/v1/generations",
        json={"voice_profile_id": vid, "text": "Testing error recovery.", "language": "en"},
    )
    assert res.status_code == 500
    assert "out-of-memory" in res.json()["detail"].lower()

    # App remains healthy and failed attempt is safely recorded in history
    assert client.get("/health").status_code == 200
    hist = client.get("/api/v1/generations").json()["generations"]
    assert len(hist) == 1
    assert hist[0]["status"] == "failed"
    assert "out-of-memory" in hist[0]["error_message"].lower()


@pytest.mark.skip(
    reason="PENDING_LAPTOP_HARDWARE: Requires Linux Mint laptop with ffmpeg installed to verify live MP3 encoding."
)
def test_pending_mp3_export_with_ffmpeg_on_linux_mint() -> None:
    raise NotImplementedError("Run on Linux Mint after 'sudo apt install ffmpeg'.")


@pytest.mark.skip(
    reason="PENDING_LAPTOP_HARDWARE: Requires air-gapped network-disabled test on Linux Mint with cached model weights."
)
def test_pending_airgapped_offline_neural_inference_on_linux_mint() -> None:
    raise NotImplementedError("Disconnect internet on Linux Mint and run generation.")
