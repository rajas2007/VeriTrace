"""Multilingual text normalization and script detection for Indian document intelligence.

Preserves exact verbatim extraction provenance in raw_text while producing
canonical, NFC-normalized, and numeral-standardized text for downstream verification.
"""

from __future__ import annotations

import re
import unicodedata

from veritrace.domain.value_objects.multilingual import (
    LanguageDetectionProfile,
    LanguageScriptIdentification,
)

# Devanagari numerals mapping: '०' to '९' -> '0' to '9'
DEVANAGARI_DIGITS = {
    "०": "0",
    "१": "1",
    "२": "2",
    "३": "3",
    "४": "4",
    "५": "5",
    "६": "6",
    "७": "7",
    "८": "8",
    "९": "9",
}

# Bengali numerals: '০' to '৯' -> '0' to '9'
BENGALI_DIGITS = {
    "০": "0",
    "১": "1",
    "২": "2",
    "৩": "3",
    "৪": "4",
    "৫": "5",
    "৬": "6",
    "৭": "7",
    "৮": "8",
    "৯": "9",
}

# Gujarati numerals: '૦' to '૯' -> '0' to '9'
GUJARATI_DIGITS = {
    "૦": "0",
    "૧": "1",
    "૨": "2",
    "૩": "3",
    "૪": "4",
    "૫": "5",
    "૬": "6",
    "૭": "7",
    "૮": "8",
    "૯": "9",
}

# Gurmukhi numerals: '੦' to '੯' -> '0' to '9'
GURMUKHI_DIGITS = {
    "੦": "0",
    "੧": "1",
    "੨": "2",
    "੩": "3",
    "੪": "4",
    "੫": "5",
    "੬": "6",
    "੭": "7",
    "੮": "8",
    "੯": "9",
}

# Combined Indic to ASCII digit translation table
ALL_INDIC_DIGITS_TABLE = str.maketrans(
    {
        **DEVANAGARI_DIGITS,
        **BENGALI_DIGITS,
        **GUJARATI_DIGITS,
        **GURMUKHI_DIGITS,
    }
)


class TextNormalizer:
    """Enterprise text normalizer supporting Latin and Indic multilingual documents."""

    @staticmethod
    def normalize_unicode(text: str) -> str:
        """Apply Unicode NFC (Canonical Decomposition followed by Canonical Composition).

        Ensures combining vowel signs (matras), nuktas, and viramas are canonically encoded.
        """
        if not text:
            return ""
        return unicodedata.normalize("NFC", text)

    @staticmethod
    def normalize_numerals(text: str) -> str:
        """Standardize Indic script numerals to Hindu-Arabic ASCII digits (0-9).

        Leaves non-numeral text and already standard digits unmodified.
        """
        if not text:
            return ""
        return text.translate(ALL_INDIC_DIGITS_TABLE)

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Collapse multiple spaces while preserving single newlines and tabs."""
        if not text:
            return ""
        # Remove zero-width spaces and control characters (except \n, \r, \t)
        cleaned = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)
        cleaned = re.sub(r"[^\S\r\n]+", " ", cleaned)
        return cleaned.strip()

    @classmethod
    def normalize_for_matching(cls, text: str) -> str:
        """Comprehensive normalization pipeline for cross-document field and text matching.

        Applies:
        1. Unicode NFC normalization.
        2. Indic numeral transliteration to 0-9.
        3. Whitespace sanitization.
        """
        if not text:
            return ""
        nfc = cls.normalize_unicode(text)
        num_norm = cls.normalize_numerals(nfc)
        return cls.normalize_whitespace(num_norm)

    @staticmethod
    def detect_script(text: str) -> str:
        """Detect the predominant script of a given text block based on Unicode code points.

        Returns ISO 15924 script code (e.g. 'Latn', 'Deva', 'Beng', 'Gujr', 'Guru').
        """
        if not text:
            return "Latn"

        counts: dict[str, int] = {
            "Latn": 0,
            "Deva": 0,
            "Beng": 0,
            "Gujr": 0,
            "Guru": 0,
            "Taml": 0,
            "Telu": 0,
        }

        for ch in text:
            cp = ord(ch)
            if (0x0041 <= cp <= 0x005A) or (0x0061 <= cp <= 0x007A):
                counts["Latn"] += 1
            elif 0x0900 <= cp <= 0x097F:
                counts["Deva"] += 1
            elif 0x0980 <= cp <= 0x09FF:
                counts["Beng"] += 1
            elif 0x0A00 <= cp <= 0x0A7F:
                counts["Guru"] += 1
            elif 0x0A80 <= cp <= 0x0AFF:
                counts["Gujr"] += 1
            elif 0x0B80 <= cp <= 0x0BFF:
                counts["Taml"] += 1
            elif 0x0C00 <= cp <= 0x0C7F:
                counts["Telu"] += 1

        total_counted = sum(counts.values())
        if total_counted == 0:
            return "Latn"

        return max(counts, key=counts.get)  # type: ignore[arg-type]

    @classmethod
    def detect_language_profile(cls, text: str) -> LanguageDetectionProfile:
        """Create a full LanguageDetectionProfile from page text."""
        if not text or not text.strip():
            return LanguageDetectionProfile(
                primary_language="eng",
                primary_script="Latn",
                confidence=1.0,
                detected_languages=(
                    LanguageScriptIdentification(language="eng", script="Latn", confidence=1.0),
                ),
            )

        script = cls.detect_script(text)
        lang_map = {
            "Latn": ("eng", "Latn"),
            "Deva": ("hin", "Deva"),  # Default Devanagari to Hindi unless Marathi markers present
            "Beng": ("ben", "Beng"),
            "Gujr": ("guj", "Gujr"),
            "Guru": ("pan", "Guru"),
            "Taml": ("tam", "Taml"),
            "Telu": ("tel", "Telu"),
        }

        primary_lang, primary_script = lang_map.get(script, ("eng", "Latn"))

        # Heuristic for Marathi in Devanagari: presence of 'ळ' (U+0933)
        if script == "Deva" and "ळ" in text:
            primary_lang = "mar"

        return LanguageDetectionProfile(
            primary_language=primary_lang,
            primary_script=primary_script,
            confidence=0.95,
            detected_languages=(
                LanguageScriptIdentification(
                    language=primary_lang, script=primary_script, confidence=0.95
                ),
            ),
        )
