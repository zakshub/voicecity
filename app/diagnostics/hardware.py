"""Local hardware discovery for FastAPI diagnostics and CLI tools."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from scripts.hardware_probe import HardwareReport, probe_hardware


def get_hardware_diagnostics(target_path: Path | None = None) -> dict[str, Any]:
    report: HardwareReport = probe_hardware(target_disk_path=target_path)
    return asdict(report)
