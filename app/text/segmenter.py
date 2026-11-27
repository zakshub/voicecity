"""Deterministic script detection, Urdu/English normalization, and mixed-language segmentation."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Literal

LanguageCode = Literal["ur", "en", "mixed"]

_WHITESPACE_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"\S+")
_ACRONYM_RE = re.compile(r"\b(?:[A-Z]{2,6}|Dr\.|Mr\.|Mrs\.|Ms\.|Rs\.|PKR|USD)\b")

_URDU_DIGIT_MAP = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789",
)


@dataclass(frozen=True)
class TextSegment:
    language: Literal["ur", "en"]
    text: str


@dataclass(frozen=True)
class TextAnalysis:
    normalized_text: str
    detected_language: LanguageCode
    has_urdu_script: bool
    has_latin_script: bool
    char_count: int
    word_count: int
    segments: list[TextSegment]
    pronunciation_hints: list[str] = field(default_factory=list)


def is_urdu_char(ch: str) -> bool:
    code = ord(ch)
    return (
        0x0600 <= code <= 0x06FF
        or 0x0750 <= code <= 0x077F
        or 0x08A0 <= code <= 0x08FF
        or 0xFB50 <= code <= 0xFDFF
        or 0xFE70 <= code <= 0xFEFF
    )


def is_latin_char(ch: str) -> bool:
    return ("a" <= ch <= "z") or ("A" <= ch <= "Z")


def normalize_text(text: str, *, normalize_digits: bool = True) -> str:
    """Normalize whitespace, Arabic->Urdu letter forms, and optional Urdu/Arabic digits.

    Preserves Urdu ZWNJ (\u200c) because removing it corrupts Urdu compound words.
    """
    cleaned = text.replace("\u0643", "\u06A9")  # Arabic Kaf -> Urdu Keheh
    cleaned = cleaned.replace("\u064A", "\u06CC")  # Arabic Yeh -> Urdu Yeh
    cleaned = cleaned.replace("\u06C0", "\u06C1\u0654")  # Heh with Yeh above
    cleaned = cleaned.replace("\u200f", "").replace("\u200e", "")  # strip directional marks
    if normalize_digits:
        cleaned = cleaned.translate(_URDU_DIGIT_MAP)
    # Harmonize stray ASCII question marks immediately following Urdu characters
    cleaned = re.sub(r"([\u0600-\u06FF])\?", r"\1؟", cleaned)
    cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def _classify_token(token: str) -> Literal["ur", "en", "neutral"]:
    ur_count = sum(1 for c in token if is_urdu_char(c))
    en_count = sum(1 for c in token if is_latin_char(c))
    if ur_count > 0 and ur_count >= en_count:
        return "ur"
    if en_count > 0:
        return "en"
    return "neutral"


def _collect_hints(
    normalized: str,
    requested: LanguageCode,
    has_ur: bool,
    has_en: bool,
    segments: list[TextSegment],
) -> list[str]:
    hints: list[str] = []
    if requested == "ur" and has_en:
        hints.append(
            "English Latin words detected while Urdu-only mode is selected. Switch to "
            "'Mixed Urdu + English' if you want Latin words routed to an English engine."
        )
    if requested == "en" and has_ur:
        hints.append(
            "Urdu script detected while English-only mode is selected. Switch to "
            "'Urdu' or 'Mixed Urdu + English'."
        )
    acronyms = sorted(set(_ACRONYM_RE.findall(normalized)))
    if acronyms:
        hints.append(
            f"Abbreviations/acronyms detected ({', '.join(acronyms[:5])}). If pronunciation "
            "sounds abrupt, spell them out (e.g., 'rupees' or 'روپے' instead of 'Rs.')."
        )
    if len(normalized) > 350:
        hints.append(
            "Long passage (>350 chars): shorter 1-3 sentence chunks typically yield steadier "
            "prosody and faster local synthesis."
        )
    if requested == "mixed" and len(segments) > 6:
        hints.append(
            f"Text switches languages frequently ({len(segments)} segments). Expect brief "
            "cross-fade pauses at language boundaries."
        )
    return hints


def analyze_and_segment(
    raw_text: str,
    requested_language: LanguageCode = "mixed",
) -> TextAnalysis:
    """Analyze script composition, normalize Urdu/English forms, and split language runs."""
    normalized = normalize_text(raw_text)
    if not normalized:
        return TextAnalysis(
            normalized_text="",
            detected_language="en" if requested_language == "en" else "ur",
            has_urdu_script=False,
            has_latin_script=False,
            char_count=0,
            word_count=0,
            segments=[],
            pronunciation_hints=[],
        )

    has_ur = any(is_urdu_char(c) for c in normalized)
    has_en = any(is_latin_char(c) for c in normalized)

    if has_ur and has_en:
        detected: LanguageCode = "mixed"
    elif has_ur:
        detected = "ur"
    elif has_en:
        detected = "en"
    else:
        detected = "en" if requested_language == "en" else "ur"

    if requested_language in ("ur", "en"):
        segs = [TextSegment(language=requested_language, text=normalized)]
        return TextAnalysis(
            normalized_text=normalized,
            detected_language=detected,
            has_urdu_script=has_ur,
            has_latin_script=has_en,
            char_count=len(normalized),
            word_count=len(normalized.split()),
            segments=segs,
            pronunciation_hints=_collect_hints(
                normalized, requested_language, has_ur, has_en, segs
            ),
        )

    tokens = _TOKEN_RE.findall(normalized)
    default_lang: Literal["ur", "en"] = "ur" if has_ur else "en"
    raw_pairs: list[tuple[Literal["ur", "en"], str]] = []
    pending_neutral: list[str] = []

    for tok in tokens:
        cls = _classify_token(tok)
        if cls == "neutral":
            if raw_pairs:
                prev_lang, prev_tok = raw_pairs[-1]
                raw_pairs[-1] = (prev_lang, f"{prev_tok} {tok}")
            else:
                pending_neutral.append(tok)
            continue

        if pending_neutral:
            prefix = " ".join(pending_neutral)
            tok = f"{prefix} {tok}"
            pending_neutral.clear()

        if raw_pairs and raw_pairs[-1][0] == cls:
            raw_pairs[-1] = (cls, f"{raw_pairs[-1][1]} {tok}")
        else:
            raw_pairs.append((cls, tok))

    if pending_neutral:
        raw_pairs.append((default_lang, " ".join(pending_neutral)))

    segments = [TextSegment(language=lang, text=txt) for lang, txt in raw_pairs]
    return TextAnalysis(
        normalized_text=normalized,
        detected_language=detected,
        has_urdu_script=has_ur,
        has_latin_script=has_en,
        char_count=len(normalized),
        word_count=len(tokens),
        segments=segments,
        pronunciation_hints=_collect_hints(
            normalized, requested_language, has_ur, has_en, segments
        ),
    )
