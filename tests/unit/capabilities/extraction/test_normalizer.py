"""Unit tests for TextNormalizer."""

from veritrace.capabilities.extraction.normalizer import TextNormalizer


def test_normalize_unicode_nfc():
    """Verify Unicode canonical composition works across combined code points."""
    # 'e' + combining acute accent -> single 'é' code point
    decomposed = "e\u0301"
    composed = "é"
    assert TextNormalizer.normalize_unicode(decomposed) == composed


def test_normalize_numerals_devanagari():
    """Verify Devanagari numerals are converted to standard 0-9 digits."""
    # Devanagari "१२३४५६७८९०" -> "1234567890"
    devanagari_str = "एकूण रक्कम: ₹१,८५,०००/-"
    normalized = TextNormalizer.normalize_numerals(devanagari_str)
    assert "1,85,000" in normalized


def test_normalize_numerals_other_indic_scripts():
    """Verify Bengali, Gujarati, and Gurmukhi numerals are converted."""
    bengali = "১২৩৪৫"
    gujarati = "૧૨૩૪૫"
    gurmukhi = "੧੨੩੪੫"

    assert TextNormalizer.normalize_numerals(bengali) == "12345"
    assert TextNormalizer.normalize_numerals(gujarati) == "12345"
    assert TextNormalizer.normalize_numerals(gurmukhi) == "12345"


def test_normalize_whitespace():
    """Verify multiple spaces and zero-width spaces are collapsed."""
    dirty = "Hello \u200b  World \t  \n Second   Line "
    cleaned = TextNormalizer.normalize_whitespace(dirty)
    assert "Hello World" in cleaned
    assert "Second Line" in cleaned


def test_normalize_for_matching():
    """Verify end-to-end normalization for field comparison."""
    input_text = "वेतन: ₹ १,८५,००० /-"
    normalized = TextNormalizer.normalize_for_matching(input_text)
    assert "1,85,000" in normalized


def test_detect_script_latin():
    """Verify Latin script identification."""
    assert TextNormalizer.detect_script("Invoice Number INV-2026-001") == "Latn"


def test_detect_script_devanagari():
    """Verify Devanagari script identification."""
    assert TextNormalizer.detect_script("वेतन पत्रक") == "Deva"


def test_detect_language_profile_hindi():
    """Verify Hindi identification for Devanagari text."""
    profile = TextNormalizer.detect_language_profile("प्रमाणपत्र संख्या")
    assert profile.primary_language == "hin"
    assert profile.primary_script == "Deva"


def test_detect_language_profile_marathi():
    """Verify Marathi identification when Marathi characteristic glyphs (ळ) are present."""
    # Presence of 'ळ' identifies Marathi
    profile = TextNormalizer.detect_language_profile("एकूण मिळणारी रक्कम")
    assert profile.primary_language == "mar"
    assert profile.primary_script == "Deva"
