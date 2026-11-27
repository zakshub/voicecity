"""Milestone 2 automated tests for VoiceCity backend, audio preprocessing, and storage."""

from __future__ import annotations

import math
from pathlib import Path
import struct
import wave

from fastapi.testclient import TestClient

from app.audio.service import inspect_wav, prepare_reference_segment, stitch_wav_segments
from app.core.config import Settings
from app.main import create_app
from app.text.segmenter import analyze_and_segment


def _make_tone_wav(
    path: Path,
    duration_sec: float = 10.0,
    rate: int = 24000,
    channels: int = 1,
    freq: float = 220.0,
    amplitude: float = 0.4,
    leading_silence_sec: float = 0.0,
) -> Path:
    total_frames = int(duration_sec * rate)
    silence_frames = int(leading_silence_sec * rate)
    samples: list[int] = []
    for i in range(total_frames):
        val = (
            0
            if i < silence_frames
            else int(32767 * amplitude * math.sin(2.0 * math.pi * freq * (i / float(rate))))
        )
        for _ in range(channels):
            samples.append(val)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack("<" + "h" * len(samples), *samples))
    return path


def _test_client(tmp_path: Path) -> TestClient:
    cfg = Settings(
        environment="test",
        host="127.0.0.1",
        port=8765,
        data_dir=tmp_path / "data",
        model_dir=tmp_path / "models",
        allow_remote_inference=False,
    )
    return TestClient(create_app(settings=cfg))


def test_audio_inspection_and_slicing_preserves_original(tmp_path: Path) -> None:
    src = _make_tone_wav(
        tmp_path / "two_min_like.wav",
        duration_sec=24.0,
        rate=44100,
        channels=2,
        leading_silence_sec=8.0,
    )
    orig_bytes = src.read_bytes()

    info = inspect_wav(src)
    assert info.is_valid is True
    assert info.sample_rate_hz == 44100
    assert info.channels == 2
    assert 23.9 <= info.duration_seconds <= 24.1

    ref_out = tmp_path / "ref.wav"
    prepared = prepare_reference_segment(src, ref_out, target_duration_sec=8.0)
    assert ref_out.is_file()
    # Active speech starts at 8.0s after leading silence
    assert prepared.start_seconds >= 7.5
    assert 7.8 <= prepared.duration_seconds <= 8.2
    assert prepared.sample_rate_hz == 24000
    assert prepared.channels == 1
    # Original source audio must be untouched
    assert src.read_bytes() == orig_bytes


def test_wav_stitcher_combines_segments(tmp_path: Path) -> None:
    s1 = _make_tone_wav(tmp_path / "s1.wav", duration_sec=0.5, rate=16000)
    s2 = _make_tone_wav(tmp_path / "s2.wav", duration_sec=0.5, rate=24000)
    out = tmp_path / "stitched.wav"
    dur, rate = stitch_wav_segments([s1, s2], out, target_sample_rate=24000, pause_ms=100)
    assert rate == 24000
    assert 1.05 <= dur <= 1.15
    assert out.is_file()


def test_urdu_english_mixed_text_segmentation() -> None:
    text = "آج شام کو ہم اپنی نئی application کا launch review 2026 میں کریں گے۔"
    analysis = analyze_and_segment(text, requested_language="mixed")
    assert analysis.detected_language == "mixed"
    assert analysis.has_urdu_script is True
    assert analysis.has_latin_script is True
    langs = [seg.language for seg in analysis.segments]
    assert langs == ["ur", "en", "ur", "en", "ur"]
    assert "application" in analysis.segments[1].text
    assert "launch review" in analysis.segments[3].text


def test_voice_profile_lifecycle_and_validation(tmp_path: Path) -> None:
    client = _test_client(tmp_path)
    wav_file = _make_tone_wav(tmp_path / "my_voice.wav", duration_sec=9.0, rate=24000)

    # Reject without ownership confirmation
    res_no_consent = client.post(
        "/api/v1/voices/import",
        data={"display_name": "Zak Personal", "ownership_confirmed": "false"},
        files={"file": ("my_voice.wav", wav_file.read_bytes(), "audio/wav")},
    )
    assert res_no_consent.status_code == 400

    # Reject invalid non-WAV content even with .wav extension
    res_bad = client.post(
        "/api/v1/voices/import",
        data={"display_name": "Bad File", "ownership_confirmed": "true"},
        files={"file": ("../evil.wav", b"not a real wav file at all" * 5, "audio/wav")},
    )
    assert res_bad.status_code == 400

    # Successful import with path-traversal filename safely sanitized
    res_ok = client.post(
        "/api/v1/voices/import",
        data={
            "display_name": "Zak Studio Voice",
            "ownership_confirmed": "true",
            "notes": "Two minute reference test",
        },
        files={"file": ("../../zak_voice.wav", wav_file.read_bytes(), "audio/wav")},
    )
    assert res_ok.status_code == 201
    voice = res_ok.json()["voice"]
    vid = voice["id"]
    assert voice["display_name"] == "Zak Studio Voice"
    assert voice["source_audio_name"] == "zak_voice.wav"
    assert voice["has_reference_segment"] is True

    # Stream source and reference audio
    assert client.get(f"/api/v1/voices/{vid}/source-audio").status_code == 200
    assert client.get(f"/api/v1/voices/{vid}/reference-audio").status_code == 200

    # Rename & update transcript
    res_patch = client.patch(
        f"/api/v1/voices/{vid}",
        json={"display_name": "Zak Primary", "reference_transcript": "السلام علیکم"},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["voice"]["display_name"] == "Zak Primary"
    assert res_patch.json()["voice"]["reference_transcript"] == "السلام علیکم"

    # Re-prepare reference segment with 6s duration
    res_prep = client.post(
        f"/api/v1/voices/{vid}/prepare",
        json={"target_duration_seconds": 6.0},
    )
    assert res_prep.status_code == 200
    assert 5.8 <= res_prep.json()["voice"]["reference_duration_seconds"] <= 6.2

    # Generation request honestly reports 503 when ML weights are not installed
    res_gen = client.post(
        "/api/v1/generations",
        json={"voice_profile_id": vid, "text": "السلام علیکم", "language": "ur"},
    )
    assert res_gen.status_code == 503
    assert res_gen.json()["detail"]["error"] == "engine_not_ready"

    # Delete removes DB entry and files on disk
    profile_dir = tmp_path / "data" / "voice_profiles" / vid
    assert profile_dir.is_dir()
    res_del = client.delete(f"/api/v1/voices/{vid}")
    assert res_del.status_code == 200
    assert not profile_dir.exists()
    assert client.get(f"/api/v1/voices/{vid}").status_code == 404


def test_settings_and_diagnostics_endpoints(tmp_path: Path) -> None:
    client = _test_client(tmp_path)
    diag = client.get("/api/v1/diagnostics")
    assert diag.status_code == 200
    body = diag.json()
    assert body["privacy"]["remote_inference_enabled"] is False
    assert body["privacy"]["bind_host"] == "127.0.0.1"

    patch_res = client.patch(
        "/api/v1/settings",
        json={"default_language": "mixed", "default_speed": 1.1, "default_expression": "warm"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["preferences"]["default_language"] == "mixed"

    # Reload a fresh app instance on the same data_dir and verify SQLite persistence
    client2 = _test_client(tmp_path)
    got = client2.get("/api/v1/settings").json()["preferences"]
    assert got["default_language"] == "mixed"
    assert got["default_speed"] == 1.1
    assert got["default_expression"] == "warm"
