"""Deterministic script detection and segmentation for Urdu, English, and Mixed text."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

LanguageCode = Literal["ur", "en", "mixed"]

_WHITESPACE_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"\S+")


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


def normalize_text(text: str) -> str:
    """Normalize whitespace and standard Urdu/Arabic presentation quirks."""
    # Normalize Arabic Kaf/Yeh variants to standard Urdu forms where appropriate
    cleaned = text.replace("\u0643", "\u06A9")  # Arabic Kaf -> Urdu Keheh
    cleaned = cleaned.replace("\u064A", "\u06CC")  # Arabic Yeh -> Farsi/Urdu Yeh
    cleaned = cleaned.replace("\u200f", "").replace("\u200e", "")
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


def analyze_and_segment(
    raw_text: str,
    requested_language: LanguageCode = "mixed",
) -> TextAnalysis:
    """Analyze script composition and split mixed text into contiguous language runs."""
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

    # If user explicitly locked pure Urdu or pure English, keep as a single segment
    if requested_language in ("ur", "en"):
        return TextAnalysis(
            normalized_text=normalized,
            detected_language=detected,
            has_urdu_script=has_ur,
            has_latin_script=has_en,
            char_count=len(normalized),
            word_count=len(normalized.split()),
            segments=[TextSegment(language=requested_language, text=normalized)],
        )

    # Mixed mode: group tokens into contiguous Urdu vs English segments,
    # attaching neutral numbers/punctuation to the surrounding language span.
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
    )
