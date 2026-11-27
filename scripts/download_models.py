#!/usr/bin/env python3
"""Consent-driven local model weight downloader for VoiceCity (Linux Mint).

Downloads commercially compatible model weights directly into VOICECITY_MODEL_DIR
so runtime speech synthesis can execute strictly offline.

Safety guards:
- Prints exact code and weight licenses before downloading.
- Refuses to download multi-GB checkpoints onto Android/Termux PRoot environments.
- Verifies adequate free disk space before starting any download.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.config import load_settings  # noqa: E402
from scripts.hardware_probe import probe_hardware  # noqa: E402

MODEL_SPECS: dict[str, dict[str, object]] = {
    "indic_parler_openvoice": {
        "display_name": "Indic Parler-TTS + OpenVoice v2 (Commercial Default)",
        "min_disk_gb": 10.0,
        "estimated_download_gb": 4.2,
        "licenses": [
            "ai4bharat/indic-parler-tts — Apache-2.0 (commercial use permitted)",
            "myshell-ai/OpenVoiceV2 — MIT (commercial use permitted)",
        ],
        "repos": [
            ("ai4bharat/indic-parler-tts", "indic_parler_tts", None),
            ("myshell-ai/OpenVoiceV2", "openvoice_v2", ["checkpoints_v2/converter/*"]),
        ],
    },
    "f5_tts_urdu": {
        "display_name": "F5-TTS OpenBible Urdu + Vocos (Direct Zero-Shot · Urdu Only)",
        "min_disk_gb": 12.0,
        "estimated_download_gb": 5.5,
        "licenses": [
            "SWivid/F5-TTS code — MIT",
            "multilingual-tts/F5-TTS-OpenBible-Urdu weights — CC-BY-SA-4.0 (Attribution + ShareAlike)",
            "charactr/vocos-mel-24khz vocoder — MIT",
        ],
        "repos": [
            ("multilingual-tts/F5-TTS-OpenBible-Urdu", "f5_tts_urdu", None),
            ("charactr/vocos-mel-24khz", "vocos", None),
        ],
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Download local VoiceCity speech model weights")
    parser.add_argument(
        "--engine",
        choices=sorted(MODEL_SPECS.keys()),
        default="indic_parler_openvoice",
    )
    parser.add_argument("--model-dir", type=Path, default=None, help="Override VOICECITY_MODEL_DIR")
    parser.add_argument("--yes", action="store_true", help="Skip interactive license confirmation")
    parser.add_argument(
        "--allow-mobile-override",
        action="store_true",
        help="Bypass mobile/PRoot safety guard (NOT recommended)",
    )
    args = parser.parse_args()

    cfg = load_settings()
    model_dir = (args.model_dir or cfg.model_dir).expanduser().resolve()
    spec = MODEL_SPECS[args.engine]
    hw = probe_hardware(target_disk_path=model_dir)

    print(f"=== VoiceCity Local Model Setup: {spec['display_name']} ===")
    print(f"Target directory:   {model_dir}")
    print(f"Estimated download: ~{spec['estimated_download_gb']} GB")
    print(f"Free disk space:    {hw.disk_free_gb} GB")
    print("Licenses:")
    for lic in spec["licenses"]:  # type: ignore[attr-defined]
        print(f"  - {lic}")

    if hw.is_mobile_proot_env and not args.allow_mobile_override:
        print(
            "\nBLOCKED: Detected Android/Termux PRoot phone environment. "
            "Do not download multi-GB weights onto the phone; run this script on Linux Mint.",
            file=sys.stderr,
        )
        return 1

    min_gb = float(spec["min_disk_gb"])  # type: ignore[arg-type]
    if hw.disk_free_gb < min_gb:
        print(
            f"\nERROR: Need at least {min_gb:.1f} GB free disk space, "
            f"but only {hw.disk_free_gb:.1f} GB available.",
            file=sys.stderr,
        )
        return 1

    if not args.yes:
        reply = input("\nProceed with local download under the licenses above? [y/N]: ").strip()
        if reply.lower() not in ("y", "yes"):
            print("Cancelled by user.")
            return 0

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print(
            "ERROR: huggingface_hub is not installed. Run "
            "'bash scripts/install_linux_mint.sh --with-engine " + args.engine + "' first.",
            file=sys.stderr,
        )
        return 1

    model_dir.mkdir(parents=True, exist_ok=True)
    for repo_id, subdir, allow_patterns in spec["repos"]:  # type: ignore[attr-defined]
        target = model_dir / subdir
        print(f"\nDownloading {repo_id} -> {target} ...")
        kwargs: dict[str, object] = {
            "repo_id": repo_id,
            "local_dir": str(target),
        }
        if allow_patterns is not None:
            kwargs["allow_patterns"] = allow_patterns
        snapshot_download(**kwargs)

        # Normalize OpenVoiceV2 nested checkpoints_v2/converter -> converter/
        nested = target / "checkpoints_v2" / "converter"
        flat = target / "converter"
        if nested.is_dir() and not flat.exists():
            flat.parent.mkdir(parents=True, exist_ok=True)
            nested.rename(flat)

    print("\nLocal model download complete. VoiceCity can now run offline using these weights.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
