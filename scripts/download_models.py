#!/usr/bin/env python3
"""Consent-driven local model weight downloader and offline verifier for VoiceCity (Linux Mint).

Separates permissive commercial models from optional ShareAlike models and experimental pipelines.
Never downloads multi-GB weights onto an Android/Termux PRoot phone environment.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.config import load_settings  # noqa: E402
from scripts.hardware_probe import probe_hardware  # noqa: E402

MODEL_SPECS: dict[str, dict[str, object]] = {
    "qwen3_tts_en": {
        "display_name": "Qwen3-TTS 0.6B-Base (Reference-Audio Voice Cloning · English Only)",
        "capability_class": "reference_voice_cloning",
        "license_category": "permissive_commercial",
        "min_disk_gb": 6.0,
        "estimated_download_gb": 2.52,
        "licenses": [
            "QwenLM/Qwen3-TTS code — Apache-2.0 (permissive commercial)",
            "Qwen/Qwen3-TTS-12Hz-0.6B-Base weights — Apache-2.0 (permissive commercial; NO native Urdu)",
        ],
        "repos": [
            ("Qwen/Qwen3-TTS-12Hz-0.6B-Base", "qwen3_tts_0.6b_base", None),
        ],
        "verify_files": ["qwen3_tts_0.6b_base/config.json"],
    },
    "f5_tts_urdu": {
        "display_name": "F5-TTS OpenBible Urdu + Vocos (Reference-Audio Voice Cloning · Urdu Only)",
        "capability_class": "reference_voice_cloning",
        "license_category": "share_alike_optional",
        "min_disk_gb": 12.0,
        "estimated_download_gb": 5.5,
        "licenses": [
            "SWivid/F5-TTS code — MIT",
            "multilingual-tts/F5-TTS-OpenBible-Urdu weights — CC-BY-SA-4.0 (OPTIONAL ShareAlike; Attribution + ShareAlike on modified weights)",
            "charactr/vocos-mel-24khz vocoder — MIT",
        ],
        "repos": [
            ("multilingual-tts/F5-TTS-OpenBible-Urdu", "f5_tts_urdu", None),
            ("charactr/vocos-mel-24khz", "vocos", None),
        ],
        "verify_files": [
            "f5_tts_urdu/model_last.pt",
            "f5_tts_urdu/vocab.txt",
            "vocos/config.yaml",
        ],
    },
    "dual_cloning": {
        "display_name": "Dual Cloning Bundle: F5-TTS Urdu (CC-BY-SA-4.0) + Qwen3-TTS English (Apache-2.0)",
        "capability_class": "reference_voice_cloning",
        "license_category": "share_alike_optional",
        "min_disk_gb": 18.0,
        "estimated_download_gb": 8.02,
        "licenses": [
            "Urdu: SWivid/F5-TTS (MIT) + F5-TTS-OpenBible-Urdu (CC-BY-SA-4.0 optional ShareAlike) + Vocos (MIT)",
            "English: QwenLM/Qwen3-TTS (Apache-2.0) + Qwen3-TTS-12Hz-0.6B-Base (Apache-2.0 permissive commercial)",
        ],
        "repos": [
            ("multilingual-tts/F5-TTS-OpenBible-Urdu", "f5_tts_urdu", None),
            ("charactr/vocos-mel-24khz", "vocos", None),
            ("Qwen/Qwen3-TTS-12Hz-0.6B-Base", "qwen3_tts_0.6b_base", None),
        ],
        "verify_files": [
            "f5_tts_urdu/model_last.pt",
            "f5_tts_urdu/vocab.txt",
            "vocos/config.yaml",
            "qwen3_tts_0.6b_base/config.json",
        ],
    },
    "indic_parler_tts": {
        "display_name": "AI4Bharat Indic Parler-TTS (Standard TTS ONLY — NOT Voice Cloning)",
        "capability_class": "standard_tts",
        "license_category": "permissive_commercial",
        "min_disk_gb": 10.0,
        "estimated_download_gb": 4.0,
        "licenses": [
            "huggingface/parler-tts code — Apache-2.0",
            "ai4bharat/indic-parler-tts weights — Apache-2.0 (Standard synthetic TTS; does NOT clone user WAV)",
        ],
        "repos": [
            ("ai4bharat/indic-parler-tts", "indic_parler_tts", None),
        ],
        "verify_files": ["indic_parler_tts/config.json"],
    },
    "openvoice_v2_converter": {
        "display_name": "MyShell OpenVoice v2 Tone Color Converter (Voice Conversion ONLY · Urdu NOT Native)",
        "capability_class": "voice_conversion",
        "license_category": "permissive_commercial",
        "min_disk_gb": 2.0,
        "estimated_download_gb": 0.14,
        "licenses": [
            "myshell-ai/OpenVoice code & OpenVoiceV2 weights — MIT (Native EN/ES/FR/ZH/JA/KO; Urdu is NOT native)",
        ],
        "repos": [
            ("myshell-ai/OpenVoiceV2", "openvoice_v2", ["checkpoints_v2/converter/*"]),
        ],
        "verify_files": [
            "openvoice_v2/converter/checkpoint.pth",
            "openvoice_v2/converter/config.json",
        ],
    },
}


def verify_local_files(model_dir: Path, engine_id: str) -> int:
    spec = MODEL_SPECS[engine_id]
    print(f"=== Offline Verification: {spec['display_name']} ===")
    print(f"Model directory: {model_dir}")
    all_ok = True
    for rel in spec["verify_files"]:  # type: ignore[attr-defined]
        full = model_dir / rel
        if full.is_file():
            size_mb = full.stat().st_size / (1024 * 1024)
            digest = ""
            if full.stat().st_size <= 5 * 1024 * 1024:
                digest = f" sha256={hashlib.sha256(full.read_bytes()).hexdigest()[:16]}"
            print(f"  [OK]      {rel} ({size_mb:.2f} MB){digest}")
        else:
            print(f"  [MISSING] {rel}")
            all_ok = False
    return 0 if all_ok else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Download or verify local VoiceCity model weights")
    parser.add_argument(
        "--engine",
        choices=sorted(MODEL_SPECS.keys()),
        default="dual_cloning",
    )
    parser.add_argument("--model-dir", type=Path, default=None, help="Override VOICECITY_MODEL_DIR")
    parser.add_argument("--verify-only", action="store_true", help="Verify local files offline only")
    parser.add_argument("--yes", action="store_true", help="Skip interactive license confirmation")
    parser.add_argument(
        "--allow-mobile-override",
        action="store_true",
        help="Bypass mobile/PRoot safety guard (NOT recommended)",
    )
    args = parser.parse_args()

    cfg = load_settings()
    model_dir = (args.model_dir or cfg.model_dir).expanduser().resolve()

    if args.verify_only:
        return verify_local_files(model_dir, args.engine)

    spec = MODEL_SPECS[args.engine]
    hw = probe_hardware(target_disk_path=model_dir)

    print(f"=== VoiceCity Local Model Download: {spec['display_name']} ===")
    print(f"Capability class:   {spec['capability_class']}")
    print(f"License category:   {spec['license_category']}")
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
            f"ERROR: huggingface_hub is not installed. Run "
            f"'bash scripts/install_linux_mint.sh --with-engine {args.engine}' first.",
            file=sys.stderr,
        )
        return 1

    model_dir.mkdir(parents=True, exist_ok=True)
    for repo_id, subdir, allow_patterns in spec["repos"]:  # type: ignore[attr-defined]
        target = model_dir / subdir
        print(f"\nDownloading {repo_id} -> {target} ...")
        kwargs: dict[str, object] = {"repo_id": repo_id, "local_dir": str(target)}
        if allow_patterns is not None:
            kwargs["allow_patterns"] = allow_patterns
        snapshot_download(**kwargs)

        nested = target / "checkpoints_v2" / "converter"
        flat = target / "converter"
        if nested.is_dir() and not flat.exists():
            flat.parent.mkdir(parents=True, exist_ok=True)
            nested.rename(flat)

    print("\nVerifying downloaded files...")
    return verify_local_files(model_dir, args.engine)


if __name__ == "__main__":
    raise SystemExit(main())
