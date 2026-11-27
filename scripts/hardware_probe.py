#!/usr/bin/env python3
"""Cross-platform Linux hardware and runtime probe for VoiceCity.

Uses only the Python standard library so it works before any dependencies are installed.
Safely distinguishes the Android/Termux PRoot workflow container from the target Linux Mint
laptop so heavyweight ML downloads or inference are never run accidentally on the phone.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys


@dataclass(frozen=True)
class GpuInfo:
    vendor: str
    name: str
    vram_mb: int | None = None
    driver_version: str | None = None
    acceleration: str = "none"


@dataclass(frozen=True)
class HardwareReport:
    os_name: str
    os_pretty_name: str
    kernel_release: str
    architecture: str
    python_version: str
    is_mobile_proot_env: bool
    cpu_model: str
    cpu_logical_cores: int
    ram_total_gb: float
    ram_available_gb: float
    disk_path: str
    disk_free_gb: float
    ffmpeg_available: bool
    gpus: list[GpuInfo] = field(default_factory=list)
    cuda_available: bool = False
    recommended_device: str = "cpu"
    recommended_engine: str = "indic_parler_openvoice"
    warnings: list[str] = field(default_factory=list)


def _run_cmd(args: list[str], timeout: float = 5.0) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return completed.returncode, completed.stdout.strip()
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired, OSError):
        return 127, ""


def _read_os_pretty_name() -> str:
    os_release = Path("/etc/os-release")
    if os_release.is_file():
        for line in os_release.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip().strip('"')
    return f"{platform.system()} {platform.release()}"


def _detect_mobile_proot(kernel_release: str, arch: str) -> bool:
    if "proot" in kernel_release.lower():
        return True
    if Path("/data/data/com.termux").exists():
        return True
    if arch == "aarch64" and Path("/system/build.prop").exists():
        return True
    return False


def _read_cpu_model() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        text = cpuinfo.read_text(encoding="utf-8", errors="ignore")
        for key in ("model name", "Hardware", "Processor"):
            match = re.search(rf"^{key}\s*:\s*(.+)$", text, flags=re.MULTILINE)
            if match:
                return match.group(1).strip()
    rc, out = _run_cmd(["lscpu"])
    if rc == 0:
        for line in out.splitlines():
            if line.lower().startswith("model name:"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or "Unknown CPU"


def _read_ram_gb() -> tuple[float, float]:
    meminfo = Path("/proc/meminfo")
    total_kb = 0
    avail_kb = 0
    if meminfo.is_file():
        for line in meminfo.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.startswith("MemTotal:"):
                total_kb = int(line.split()[1])
            elif line.startswith("MemAvailable:"):
                avail_kb = int(line.split()[1])
    return round(total_kb / (1024 * 1024), 2), round(avail_kb / (1024 * 1024), 2)


def _detect_gpus() -> tuple[list[GpuInfo], bool]:
    gpus: list[GpuInfo] = []
    cuda_available = False

    # 1. NVIDIA via nvidia-smi
    nvidia_smi = shutil.which("nvidia-smi")
    if nvidia_smi:
        rc, out = _run_cmd(
            [
                nvidia_smi,
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ]
        )
        if rc == 0 and out:
            for line in out.splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    vram_mb = int(parts[1]) if parts[1].isdigit() else None
                    gpus.append(
                        GpuInfo(
                            vendor="NVIDIA",
                            name=parts[0],
                            vram_mb=vram_mb,
                            driver_version=parts[2],
                            acceleration="cuda",
                        )
                    )
                    cuda_available = True

    # 2. PCI discovery via lspci (for AMD / Intel / NVIDIA without driver)
    if not gpus:
        lspci_bin = shutil.which("lspci") or (
            "/usr/sbin/lspci" if Path("/usr/sbin/lspci").is_file() else None
        )
        if lspci_bin:
            rc, out = _run_cmd([lspci_bin, "-nn"])
            if rc == 0:
                for line in out.splitlines():
                    if re.search(r"\b(vga|3d|display)\b", line, flags=re.IGNORECASE):
                        desc = line.split(":", 2)[-1].strip()
                        vendor = "Unknown"
                        accel = "none"
                        if "nvidia" in desc.lower():
                            vendor = "NVIDIA"
                        elif "amd" in desc.lower() or "ati" in desc.lower():
                            vendor = "AMD"
                            accel = "rocm_candidate"
                        elif "intel" in desc.lower():
                            vendor = "Intel"
                        vram_mb = _read_amd_drm_vram_mb() if vendor == "AMD" else None
                        gpus.append(
                            GpuInfo(
                                vendor=vendor,
                                name=desc,
                                vram_mb=vram_mb,
                                acceleration=accel,
                            )
                        )

    return gpus, cuda_available


def _read_amd_drm_vram_mb() -> int | None:
    drm_root = Path("/sys/class/drm")
    if not drm_root.is_dir():
        return None
    for vram_file in sorted(drm_root.glob("card*/device/mem_info_vram_total")):
        try:
            raw_bytes = int(vram_file.read_text(encoding="utf-8").strip())
            return int(raw_bytes / (1024 * 1024))
        except (OSError, ValueError):
            continue
    return None


def probe_hardware(target_disk_path: Path | None = None) -> HardwareReport:
    disk_target = (target_disk_path or Path.cwd()).resolve()
    while not disk_target.exists() and disk_target != disk_target.parent:
        disk_target = disk_target.parent

    usage = shutil.disk_usage(disk_target)
    disk_free_gb = round(usage.free / (1024**3), 2)

    kernel_release = platform.release()
    arch = platform.machine()
    python_version = platform.python_version()
    is_mobile = _detect_mobile_proot(kernel_release, arch)
    ram_total_gb, ram_available_gb = _read_ram_gb()
    gpus, cuda_available = _detect_gpus()
    ffmpeg_available = shutil.which("ffmpeg") is not None

    warnings: list[str] = []
    if is_mobile:
        warnings.append(
            "Detected Termux/PRoot mobile development environment. Do not download multi-GB "
            "model checkpoints or run local neural speech inference on this device; deploy "
            "model runtimes on the target Linux Mint laptop."
        )
    if sys.version_info >= (3, 13):
        warnings.append(
            f"Python {python_version} detected. For ML model runtimes (PyTorch/torchaudio/OpenVoice), "
            "Python 3.11 or 3.12 is recommended on Linux Mint for prebuilt binary wheel support."
        )
    if disk_free_gb < 15.0:
        warnings.append(
            f"Only {disk_free_gb:.1f} GB free disk space at {disk_target}. At least 15-20 GB "
            "is recommended for local ML runtimes and cached speech model checkpoints."
        )
    if not ffmpeg_available:
        warnings.append(
            "ffmpeg is not installed. WAV preview and export work natively, while MP3 export "
            "will remain disabled until ffmpeg is installed (sudo apt install ffmpeg)."
        )

    max_vram_mb = max((g.vram_mb or 0 for g in gpus), default=0)
    recommended_device = "cuda" if cuda_available and max_vram_mb >= 4000 else "cpu"

    if recommended_device == "cpu" and not is_mobile:
        warnings.append(
            "No CUDA GPU with >=4 GB VRAM detected. Local inference will use CPU fallback, "
            "which is significantly slower than GPU generation."
        )

    return HardwareReport(
        os_name=platform.system(),
        os_pretty_name=_read_os_pretty_name(),
        kernel_release=kernel_release,
        architecture=arch,
        python_version=python_version,
        is_mobile_proot_env=is_mobile,
        cpu_model=_read_cpu_model(),
        cpu_logical_cores=os.cpu_count() or 1,
        ram_total_gb=ram_total_gb,
        ram_available_gb=ram_available_gb,
        disk_path=str(disk_target),
        disk_free_gb=disk_free_gb,
        ffmpeg_available=ffmpeg_available,
        gpus=gpus,
        cuda_available=cuda_available,
        recommended_device=recommended_device,
        recommended_engine="indic_parler_openvoice",
        warnings=warnings,
    )


def main() -> int:
    as_json = "--json" in sys.argv
    report = probe_hardware()
    if as_json:
        print(json.dumps(asdict(report), indent=2))
        return 0

    print("=== VoiceCity Hardware Probe ===")
    print(f"OS:           {report.os_pretty_name}")
    print(f"Kernel:       {report.kernel_release}")
    print(f"Architecture: {report.architecture}")
    print(f"Python:       {report.python_version}")
    print(f"Mobile/PRoot: {'YES (inference blocked by default)' if report.is_mobile_proot_env else 'No'}")
    print(f"CPU:          {report.cpu_model} ({report.cpu_logical_cores} logical cores)")
    print(f"RAM:          {report.ram_available_gb} GB available / {report.ram_total_gb} GB total")
    print(f"Disk Free:    {report.disk_free_gb} GB at {report.disk_path}")
    print(f"ffmpeg:       {'Available (MP3 export supported)' if report.ffmpeg_available else 'Not installed (WAV only)'}")
    if report.gpus:
        for idx, gpu in enumerate(report.gpus):
            vram = f"{gpu.vram_mb} MiB" if gpu.vram_mb is not None else "Unknown VRAM"
            print(f"GPU [{idx}]:      {gpu.vendor} {gpu.name} ({vram}, accel={gpu.acceleration})")
    else:
        print("GPU:          None detected")
    print(f"Device Rec:   {report.recommended_device}")
    print(f"Default Eng:  {report.recommended_engine}")
    if report.warnings:
        print("\nWarnings:")
        for w in report.warnings:
            print(f"  - {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
