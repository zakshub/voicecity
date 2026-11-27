#!/usr/bin/env python3
"""Repeatable Phase 1 Proof-of-Concept evaluation harness for VoiceCity.

Evaluates commercially compatible local speech engines against a fixed 5-prompt
Pakistani Urdu, English, and mixed Urdu-English test set.

Design guarantees:
- Never downloads or executes multi-GB ML models on the Pixel/Termux PRoot phone.
- Never fabricates passing audio-quality or hardware-speed results.
- Explicitly distinguishes installed vs. missing runtimes and pending listening reviews.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import wave

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.hardware_probe import probe_hardware  # noqa: E402


@dataclass(frozen=True)
class EvalPrompt:
    id: str
    category: str
    language: str
    text: str
    focus: str


FIXED_BENCHMARK_PROMPTS: tuple[EvalPrompt, ...] = (
    EvalPrompt(
        id="ur_formal",
        category="Urdu (Formal)",
        language="ur",
        text="السلام علیکم، وائس سٹی میں خوش آمدید۔ یہ میری اپنی آواز کا پہلا مقامی تجربہ ہے۔",
        focus="Baseline Pakistani Urdu pronunciation, rhythm, and naturalness",
    ),
    EvalPrompt(
        id="ur_phonetics",
        category="Pakistani Proper Nouns & Phonetics",
        language="ur",
        text="راولپنڈی، گوجرانوالہ، ملتان اور مظفرآباد کے موسم کا حال جاننے کے لیے رابطہ کریں۔",
        focus="Retroflex consonants (ٹ ڈ ڑ), aspirated stops, and Pakistani place names",
    ),
    EvalPrompt(
        id="en_baseline",
        category="English (Baseline)",
        language="en",
        text="Welcome to VoiceCity. This is a local-first personal voice studio running offline on Linux.",
        focus="English clarity, cadence, and timbre similarity to reference speaker",
    ),
    EvalPrompt(
        id="ur_en_mixed",
        category="Mixed Urdu-English Code-Switching",
        language="mixed",
        text="آج شام کو ہم اپنی نئی application کا launch review کریں گے، براہ کرم وقت پر جوائن کریں۔",
        focus="Seamless script transition without accent collapse or repetition artifacts",
    ),
    EvalPrompt(
        id="ur_numerals",
        category="Numbers, Dates & Currency",
        language="ur",
        text="سال 2026 میں منصوبے کا کل بجٹ 45,000 روپے اور تکمیل کی شرح 92.5 فیصد رہی۔",
        focus="Numerals, decimals, punctuation, and Pakistani currency phrasing",
    ),
)

CANDIDATE_REGISTRY: dict[str, dict[str, object]] = {
    "indic_parler_openvoice": {
        "display_name": "Indic Parler-TTS (Apache-2.0) + OpenVoice v2 (MIT)",
        "distributable_default": True,
        "code_license": "Apache-2.0 + MIT",
        "weight_license": "Apache-2.0 (ai4bharat/indic-parler-tts) + MIT (myshell-ai/OpenVoiceV2)",
        "commercial_status": "Commercially compatible (permissive)",
        "languages_claimed": ["ur", "en", "mixed"],
        "estimated_download_gb": 4.2,
        "required_python_modules": ["torch", "transformers", "parler_tts", "openvoice"],
    },
    "f5_tts_urdu": {
        "display_name": "F5-TTS (MIT) + F5-TTS-OpenBible-Urdu (CC-BY-SA-4.0)",
        "distributable_default": False,
        "code_license": "MIT",
        "weight_license": "CC-BY-SA-4.0 (multilingual-tts/F5-TTS-OpenBible-Urdu)",
        "commercial_status": "Conditional (ShareAlike required on derivative weights)",
        "languages_claimed": ["ur"],
        "estimated_download_gb": 5.5,
        "required_python_modules": ["torch", "torchaudio", "f5_tts"],
    },
}


def check_modules(module_names: list[str]) -> dict[str, bool]:
    return {name: importlib.util.find_spec(name) is not None for name in module_names}


def inspect_wav_basic(wav_path: Path) -> dict[str, object]:
    if not wav_path.is_file():
        return {"exists": False, "error": f"File not found: {wav_path}"}
    try:
        with wave.open(str(wav_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            duration = round(frames / float(rate), 2) if rate > 0 else 0.0
            return {
                "exists": True,
                "duration_seconds": duration,
                "sample_rate_hz": rate,
                "channels": channels,
                "bit_depth": sampwidth * 8,
                "suitable_duration": duration >= 5.0,
            }
    except (wave.Error, OSError) as exc:
        return {"exists": True, "error": f"Invalid WAV file: {exc}"}


def run_evaluation(
    engine_id: str,
    reference_wav: Path | None,
    output_dir: Path | None,
    dry_run: bool,
    allow_mobile_override: bool,
) -> dict[str, object]:
    hw = probe_hardware()
    candidate = CANDIDATE_REGISTRY[engine_id]
    required_mods = list(candidate["required_python_modules"])  # type: ignore[arg-type]
    module_status = check_modules(required_mods)
    missing_mods = [m for m, ok in module_status.items() if not ok]

    status = "DRY_RUN_COMPLETE"
    notes: list[str] = []

    if hw.is_mobile_proot_env and not allow_mobile_override:
        status = "BLOCKED_ON_MOBILE_PROOT_ENV"
        notes.append(
            "Host is a Termux/PRoot Android environment. Heavyweight model downloads and "
            "inference are blocked by policy. Run this script on the Linux Mint laptop."
        )
    elif missing_mods:
        status = "MODEL_RUNTIME_NOT_INSTALLED"
        notes.append(
            f"Missing Python runtime packages: {', '.join(missing_mods)}. "
            "Install them in an isolated Linux Mint venv using scripts/setup_poc_env.sh."
        )
    elif dry_run:
        notes.append("Dry-run verified environment and benchmark definitions only; no audio generated.")
    else:
        status = "READY_FOR_MODEL_WEIGHTS_AND_LISTENING_REVIEW"
        notes.append(
            "Runtime modules detected. Use app.engine.registry to execute cached offline generation "
            "and score listening quality manually (1-5) for every prompt."
        )

    result: dict[str, object] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "engine_id": engine_id,
        "candidate": candidate,
        "status": status,
        "hardware": asdict(hw),
        "runtime_modules": module_status,
        "reference_wav_check": inspect_wav_basic(reference_wav) if reference_wav else None,
        "prompts": [asdict(p) for p in FIXED_BENCHMARK_PROMPTS],
        "listening_review": {
            prompt.id: {
                "intelligibility_1_to_5": "UNTESTED",
                "pronunciation_1_to_5": "UNTESTED",
                "naturalness_1_to_5": "UNTESTED",
                "voice_similarity_1_to_5": "UNTESTED",
                "code_switching_1_to_5": "UNTESTED" if prompt.language == "mixed" else "N/A",
            }
            for prompt in FIXED_BENCHMARK_PROMPTS
        },
        "notes": notes,
    }

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        report_file = output_dir / f"poc_eval_{engine_id}.json"
        report_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="VoiceCity Phase 1 PoC Evaluation Harness")
    parser.add_argument(
        "--engine",
        choices=sorted(CANDIDATE_REGISTRY.keys()),
        default="indic_parler_openvoice",
        help="Commercially compatible engine candidate to evaluate",
    )
    parser.add_argument("--reference-wav", type=Path, default=None, help="Optional path to user WAV")
    parser.add_argument("--output-dir", type=Path, default=None, help="Optional untracked output dir")
    parser.add_argument("--dry-run", action="store_true", help="Inspect host & dependencies only")
    parser.add_argument(
        "--allow-mobile-override",
        action="store_true",
        help="Bypass PRoot phone safety guard (NOT recommended)",
    )
    args = parser.parse_args()

    result = run_evaluation(
        engine_id=args.engine,
        reference_wav=args.reference_wav,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        allow_mobile_override=args.allow_mobile_override,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
