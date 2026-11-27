"""Pure-Python WAV validation, inspection, reference slicing, stitching, and MP3 export."""

from __future__ import annotations

from array import array
from dataclasses import dataclass, field
import math
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import wave


class AudioValidationError(ValueError):
    """Raised when an uploaded or referenced audio file is invalid or unsupported."""


class AudioExportUnavailableError(RuntimeError):
    """Raised when an optional audio encoder (e.g., ffmpeg for MP3) is unavailable."""


@dataclass(frozen=True)
class AudioInspection:
    duration_seconds: float
    sample_rate_hz: int
    channels: int
    bit_depth: int
    num_frames: int
    peak_dbfs: float
    rms_dbfs: float
    clipping_samples: int
    silence_ratio: float
    is_valid: bool
    quality_status: str  # "good" | "needs_review" | "invalid"
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PreparedReferenceResult:
    reference_path: Path
    start_seconds: float
    duration_seconds: float
    sample_rate_hz: int
    channels: int
    peak_dbfs: float
    warnings: list[str] = field(default_factory=list)


def _decode_pcm_mono_float(raw_bytes: bytes, sampwidth: int, channels: int) -> list[float]:
    """Decode PCM WAV bytes into mono normalized float samples in [-1.0, 1.0]."""
    if sampwidth == 2:
        samples = array("h")
        samples.frombytes(raw_bytes)
        if sys.byteorder != "little":
            samples.byteswap()
        scale = 1.0 / 32768.0
        if channels == 1:
            return [s * scale for s in samples]
        inv_ch = scale / channels
        mono: list[float] = []
        total = len(samples)
        for idx in range(0, total - (total % channels), channels):
            acc = 0
            for c in range(channels):
                acc += samples[idx + c]
            mono.append(acc * inv_ch)
        return mono

    if sampwidth == 1:
        scale = 1.0 / 128.0
        if channels == 1:
            return [(b - 128) * scale for b in raw_bytes]
        inv_ch = scale / channels
        mono = []
        total = len(raw_bytes)
        for idx in range(0, total - (total % channels), channels):
            acc = 0
            for c in range(channels):
                acc += raw_bytes[idx + c] - 128
            mono.append(acc * inv_ch)
        return mono

    if sampwidth == 3:
        scale = 1.0 / 8388608.0
        frame_bytes = 3 * channels
        total_frames = len(raw_bytes) // frame_bytes
        mono = []
        inv_ch = scale / channels
        for f in range(total_frames):
            base = f * frame_bytes
            acc = 0
            for c in range(channels):
                off = base + c * 3
                val = int.from_bytes(raw_bytes[off : off + 3], byteorder="little", signed=True)
                acc += val
            mono.append(acc * inv_ch)
        return mono

    if sampwidth == 4:
        samples_i32 = array("i")
        samples_i32.frombytes(raw_bytes)
        if sys.byteorder != "little":
            samples_i32.byteswap()
        scale = 1.0 / 2147483648.0
        if channels == 1:
            return [s * scale for s in samples_i32]
        inv_ch = scale / channels
        mono = []
        total = len(samples_i32)
        for idx in range(0, total - (total % channels), channels):
            acc = 0
            for c in range(channels):
                acc += samples_i32[idx + c]
            mono.append(acc * inv_ch)
        return mono

    raise AudioValidationError(f"Unsupported PCM sample width: {sampwidth * 8}-bit.")


def _validate_wav_header(path: Path) -> None:
    if not path.is_file():
        raise AudioValidationError("Audio file does not exist.")
    if path.stat().st_size < 44:
        raise AudioValidationError("File is too small to be a valid WAV audio recording.")
    with path.open("rb") as fh:
        header = fh.read(12)
    if len(header) < 12 or header[0:4] != b"RIFF" or header[8:12] != b"WAVE":
        raise AudioValidationError(
            "Invalid audio container: expected an uncompressed PCM WAV file (RIFF/WAVE header)."
        )


def _to_dbfs(linear: float) -> float:
    if linear <= 1e-9:
        return -96.0
    return round(20.0 * math.log10(linear), 2)


def inspect_wav(path: Path) -> AudioInspection:
    """Validate a PCM WAV file and compute acoustic quality metrics."""
    _validate_wav_header(path)
    try:
        with wave.open(str(path), "rb") as wf:
            comp = wf.getcomptype()
            if comp != "NONE":
                raise AudioValidationError(f"Compressed WAV format ({comp}) is not supported.")
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            sample_rate = wf.getframerate()
            num_frames = wf.getnframes()

            if channels < 1 or channels > 8:
                raise AudioValidationError(f"Unsupported channel count: {channels}.")
            if sample_rate < 8000 or sample_rate > 192000:
                raise AudioValidationError(
                    f"Unsupported sample rate: {sample_rate} Hz (expected 8,000 to 192,000 Hz)."
                )
            if num_frames <= 0:
                raise AudioValidationError("WAV file contains zero audio frames.")

            duration = round(num_frames / float(sample_rate), 3)

            peak = 0.0
            sum_sq = 0.0
            total_samples = 0
            clipping_samples = 0
            silent_windows = 0
            total_windows = 0
            window_frames = max(1, int(sample_rate * 0.05))  # 50 ms windows

            while True:
                raw = wf.readframes(window_frames)
                if not raw:
                    break
                mono = _decode_pcm_mono_float(raw, sampwidth, channels)
                if not mono:
                    continue
                win_sq = 0.0
                for s in mono:
                    a = abs(s)
                    if a > peak:
                        peak = a
                    if a >= 0.995:
                        clipping_samples += 1
                    win_sq += s * s
                sum_sq += win_sq
                total_samples += len(mono)
                win_rms = math.sqrt(win_sq / len(mono))
                total_windows += 1
                if win_rms < 0.008:  # ~ -42 dBFS silence threshold
                    silent_windows += 1
    except AudioValidationError:
        raise
    except (wave.Error, EOFError, OSError, struct.error) as exc:
        raise AudioValidationError(f"Unable to decode WAV file: {exc}") from exc

    rms = math.sqrt(sum_sq / max(1, total_samples))
    peak_dbfs = _to_dbfs(peak)
    rms_dbfs = _to_dbfs(rms)
    silence_ratio = round(silent_windows / max(1, total_windows), 3)

    warnings: list[str] = []
    if duration < 3.0:
        warnings.append(
            "Recording is shorter than 3 seconds. Most zero-shot voice cloning models need "
            "at least 5 to 10 seconds of clear speech."
        )
    elif duration < 5.0:
        warnings.append(
            "Recording is between 3 and 5 seconds. 5 to 12 seconds is recommended for stronger "
            "voice similarity."
        )
    if sample_rate < 16000:
        warnings.append(
            f"Sample rate is {sample_rate} Hz. At least 16,000 Hz (24,000 Hz ideal) is recommended."
        )
    if clipping_samples > max(20, int(total_samples * 0.001)):
        warnings.append(
            f"Detected {clipping_samples} near-clipped samples (peak {peak_dbfs} dBFS). "
            "VoiceCity will attempt to pick an unclipped segment automatically."
        )
    if peak_dbfs < -24.0:
        warnings.append(
            f"Recording volume is quiet (peak {peak_dbfs} dBFS). Automatic normalization will be applied."
        )
    if silence_ratio > 0.65:
        warnings.append(
            f"Recording contains {int(silence_ratio * 100)}% low-energy silence. "
            "Automatic active-speech window extraction is enabled."
        )
    if rms_dbfs < -55.0:
        warnings.append("Recording appears nearly silent; verify the microphone input.")

    is_valid = duration >= 1.0 and rms_dbfs > -65.0
    if not is_valid:
        quality_status = "invalid"
    elif warnings:
        quality_status = "needs_review"
    else:
        quality_status = "good"

    return AudioInspection(
        duration_seconds=duration,
        sample_rate_hz=sample_rate,
        channels=channels,
        bit_depth=sampwidth * 8,
        num_frames=num_frames,
        peak_dbfs=peak_dbfs,
        rms_dbfs=rms_dbfs,
        clipping_samples=clipping_samples,
        silence_ratio=silence_ratio,
        is_valid=is_valid,
        quality_status=quality_status,
        warnings=warnings,
    )


def _resample_linear(samples: list[float], src_rate: int, dst_rate: int) -> list[float]:
    if src_rate == dst_rate or not samples:
        return samples
    ratio = src_rate / float(dst_rate)
    out_len = max(1, int(round(len(samples) / ratio)))
    out: list[float] = [0.0] * out_len
    last_idx = len(samples) - 1
    for i in range(out_len):
        pos = i * ratio
        idx = int(pos)
        if idx >= last_idx:
            out[i] = samples[last_idx]
        else:
            frac = pos - idx
            out[i] = samples[idx] * (1.0 - frac) + samples[idx + 1] * frac
    return out


def write_mono_wav_16bit(path: Path, samples: list[float], sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = array("h", (max(-32767, min(32767, int(round(s * 32767.0)))) for s in samples))
    if sys.byteorder != "little":
        pcm.byteswap()
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())


def prepare_reference_segment(
    source_path: Path,
    output_path: Path,
    target_duration_sec: float = 8.0,
    target_sample_rate: int = 24000,
) -> PreparedReferenceResult:
    """Extract the cleanest active speech window from a user recording (e.g., ~2-min WAV).

    Preserves source_path completely untouched. Downmixes to mono, selects the window with
    consistent speech energy and minimal clipping, resamples to 24 kHz, and peak-normalizes
    to -1.5 dBFS.
    """
    inspection = inspect_wav(source_path)
    if not inspection.is_valid:
        raise AudioValidationError(
            "Cannot prepare reference segment from silent or invalid audio recording."
        )

    # First pass: score 100ms chunks so we don't hold an entire multi-minute stereo file in RAM
    chunk_sec = 0.1
    chunk_frames = max(1, int(inspection.sample_rate_hz * chunk_sec))
    chunk_rms: list[float] = []
    chunk_clips: list[int] = []

    with wave.open(str(source_path), "rb") as wf:
        while True:
            raw = wf.readframes(chunk_frames)
            if not raw:
                break
            mono = _decode_pcm_mono_float(raw, wf.getsampwidth(), wf.getnchannels())
            if not mono:
                continue
            sq = 0.0
            clips = 0
            for s in mono:
                a = abs(s)
                if a >= 0.995:
                    clips += 1
                sq += s * s
            chunk_rms.append(math.sqrt(sq / len(mono)))
            chunk_clips.append(clips)

    actual_target_sec = min(target_duration_sec, inspection.duration_seconds)
    win_chunks = max(1, min(len(chunk_rms), int(round(actual_target_sec / chunk_sec))))

    best_start_chunk = 0
    best_score = -1e9
    for start in range(0, max(1, len(chunk_rms) - win_chunks + 1)):
        slice_rms = chunk_rms[start : start + win_chunks]
        slice_clips = sum(chunk_clips[start : start + win_chunks])
        active_ratio = sum(1 for r in slice_rms if r >= 0.012) / float(len(slice_rms))
        avg_rms = sum(slice_rms) / float(len(slice_rms))
        # Reward dense natural speech activity, moderate healthy loudness, penalize clipping
        score = (active_ratio * 2.5) + min(avg_rms * 8.0, 1.5) - (slice_clips * 0.02)
        if score > best_score:
            best_score = score
            best_start_chunk = start

    start_frame = int(best_start_chunk * chunk_frames)
    extract_frames = int(round(actual_target_sec * inspection.sample_rate_hz))

    with wave.open(str(source_path), "rb") as wf:
        wf.setpos(min(start_frame, max(0, wf.getnframes() - 1)))
        raw_seg = wf.readframes(extract_frames)
        mono_seg = _decode_pcm_mono_float(raw_seg, wf.getsampwidth(), wf.getnchannels())

    resampled = _resample_linear(mono_seg, inspection.sample_rate_hz, target_sample_rate)

    # Peak normalize safely to -1.5 dBFS (~0.841)
    seg_peak = max((abs(s) for s in resampled), default=0.0)
    target_peak = 0.841
    if seg_peak > 1e-5:
        gain = min(target_peak / seg_peak, 12.0)  # cap gain at +21.5 dB to avoid boosting noise floor
        normalized = [max(-0.98, min(0.98, s * gain)) for s in resampled]
    else:
        normalized = resampled

    write_mono_wav_16bit(output_path, normalized, target_sample_rate)
    final_peak = max((abs(s) for s in normalized), default=0.0)

    prep_warnings: list[str] = []
    if inspection.duration_seconds > 15.0:
        prep_warnings.append(
            f"Automatically extracted a {actual_target_sec:.1f}s clean speech segment "
            f"(starting at {best_start_chunk * chunk_sec:.1f}s) from your "
            f"{inspection.duration_seconds:.1f}s original recording."
        )

    return PreparedReferenceResult(
        reference_path=output_path,
        start_seconds=round(best_start_chunk * chunk_sec, 2),
        duration_seconds=round(len(normalized) / float(target_sample_rate), 2),
        sample_rate_hz=target_sample_rate,
        channels=1,
        peak_dbfs=_to_dbfs(final_peak),
        warnings=prep_warnings,
    )


def stitch_wav_segments(
    segment_paths: list[Path],
    output_path: Path,
    target_sample_rate: int = 24000,
    pause_ms: int = 90,
    crossfade_ms: int = 25,
) -> tuple[float, int]:
    """Concatenate multiple generated WAV segments smoothly for mixed-language synthesis."""
    if not segment_paths:
        raise AudioValidationError("No audio segments provided to stitch.")

    combined: list[float] = []
    pause_samples = int(target_sample_rate * (pause_ms / 1000.0))
    fade_samples = int(target_sample_rate * (crossfade_ms / 1000.0))

    for idx, seg_path in enumerate(segment_paths):
        with wave.open(str(seg_path), "rb") as wf:
            raw = wf.readframes(wf.getnframes())
            mono = _decode_pcm_mono_float(raw, wf.getsampwidth(), wf.getnchannels())
            seg = _resample_linear(mono, wf.getframerate(), target_sample_rate)

        if not seg:
            continue

        # Apply short edge fade-in/fade-out to eliminate clicks
        edge = min(fade_samples, len(seg) // 4)
        for i in range(edge):
            factor = i / float(max(1, edge))
            seg[i] *= factor
            seg[-(i + 1)] *= factor

        if idx > 0 and combined and pause_samples > 0:
            combined.extend([0.0] * pause_samples)
        combined.extend(seg)

    write_mono_wav_16bit(output_path, combined, target_sample_rate)
    duration = round(len(combined) / float(target_sample_rate), 3)
    return duration, target_sample_rate


def mp3_export_available() -> bool:
    return shutil.which("ffmpeg") is not None


def export_wav_to_mp3(wav_path: Path, mp3_path: Path, bitrate: str = "192k") -> Path:
    """Convert a local WAV file to MP3 via ffmpeg without invoking a shell."""
    ffmpeg_bin = shutil.which("ffmpeg")
    if ffmpeg_bin is None:
        raise AudioExportUnavailableError(
            "MP3 export requires ffmpeg, which is not installed on this system. "
            "Install it on Linux Mint with 'sudo apt install ffmpeg', or download WAV."
        )
    if not wav_path.is_file():
        raise AudioValidationError("Source WAV file not found for MP3 conversion.")

    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        [
            ffmpeg_bin,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(wav_path),
            "-codec:a",
            "libmp3lame",
            "-b:a",
            bitrate,
            str(mp3_path),
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0 or not mp3_path.is_file():
        raise AudioExportUnavailableError(
            f"ffmpeg failed to encode MP3: {completed.stderr.strip() or 'unknown error'}"
        )
    return mp3_path
