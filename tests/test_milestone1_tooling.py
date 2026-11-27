from pathlib import Path
import struct
import wave

from scripts.hardware_probe import probe_hardware
from scripts.poc_eval import FIXED_BENCHMARK_PROMPTS, inspect_wav_basic, run_evaluation


def _write_test_wav(path: Path, duration_sec: float = 6.0, rate: int = 16000) -> None:
    num_samples = int(duration_sec * rate)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack("<" + "h" * num_samples, *([0] * num_samples)))


def test_hardware_probe_returns_structured_report() -> None:
    report = probe_hardware()
    assert report.cpu_logical_cores >= 1
    assert report.disk_free_gb >= 0
    assert report.recommended_engine == "dual_cloning_router"


def test_poc_eval_has_five_multilingual_prompts() -> None:
    assert len(FIXED_BENCHMARK_PROMPTS) == 5
    langs = {p.language for p in FIXED_BENCHMARK_PROMPTS}
    assert {"ur", "en", "mixed"}.issubset(langs)


def test_poc_eval_dry_run_is_honest_about_untested_listening(tmp_path: Path) -> None:
    wav_path = tmp_path / "sample.wav"
    _write_test_wav(wav_path, duration_sec=6.0)
    wav_info = inspect_wav_basic(wav_path)
    assert wav_info["exists"] is True
    assert wav_info["suitable_duration"] is True

    result = run_evaluation(
        engine_id="f5_tts_urdu",
        reference_wav=wav_path,
        output_dir=tmp_path / "eval_out",
        dry_run=True,
        allow_mobile_override=False,
    )
    assert result["engine_id"] == "f5_tts_urdu"
    assert (tmp_path / "eval_out" / "poc_eval_f5_tts_urdu.json").is_file()
    listening = result["listening_review"]
    assert isinstance(listening, dict)
    assert listening["ur_formal"]["intelligibility_1_to_5"] == "UNTESTED"
    assert listening["en_baseline"]["intelligibility_1_to_5"] == "UNSUPPORTED_BY_ENGINE"
