"""Unit tests for multilingual and multi-script domain value objects."""

from dataclasses import FrozenInstanceError

import pytest

from veritrace.domain.exceptions import ConfidenceRangeError, ValidationError
from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.domain.value_objects.multilingual import (
    LanguageDetectionProfile,
    LanguageScriptIdentification,
    LanguageScriptRegion,
)


def test_language_script_identification_valid() -> None:
    """Verify LanguageScriptIdentification initialization."""
    ident = LanguageScriptIdentification(language="eng", script="Latn", confidence=0.98)
    assert ident.language == "eng"
    assert ident.script == "Latn"
    assert ident.confidence == 0.98


def test_language_script_identification_invalid_raises() -> None:
    """Verify invalid codes and confidence values raise appropriate errors."""
    with pytest.raises(ValidationError):
        LanguageScriptIdentification(language="", script="Latn", confidence=0.9)
    with pytest.raises(ValidationError):
        LanguageScriptIdentification(language="eng", script="  ", confidence=0.9)
    with pytest.raises(ConfidenceRangeError):
        LanguageScriptIdentification(language="eng", script="Latn", confidence=-0.1)
    with pytest.raises(ConfidenceRangeError):
        LanguageScriptIdentification(language="eng", script="Latn", confidence=1.05)


def test_language_script_region_valid() -> None:
    """Verify LanguageScriptRegion initialization and spatial bounding box."""
    bbox = NormalizedBoundingBox(ymin=0.1, xmin=0.1, ymax=0.3, xmax=0.9)
    region = LanguageScriptRegion(
        language="hin",
        script="Deva",
        confidence=0.95,
        normalized_bbox=bbox,
    )
    assert region.language == "hin"
    assert region.script == "Deva"
    assert region.confidence == 0.95
    assert region.normalized_bbox == bbox


def test_language_detection_profile_multi_script() -> None:
    """Verify multi-script profile with English header and Hindi body regions."""
    header_box = NormalizedBoundingBox(ymin=0.0, xmin=0.0, ymax=0.2, xmax=1.0)
    body_box = NormalizedBoundingBox(ymin=0.2, xmin=0.0, ymax=0.9, xmax=1.0)

    reg_eng = LanguageScriptRegion("eng", "Latn", 0.99, header_box)
    reg_hin = LanguageScriptRegion("hin", "Deva", 0.94, body_box)

    id_eng = LanguageScriptIdentification("eng", "Latn", 0.99)
    id_hin = LanguageScriptIdentification("hin", "Deva", 0.94)

    profile = LanguageDetectionProfile(
        primary_language="hin",
        primary_script="Deva",
        confidence=0.94,
        detected_languages=(id_hin, id_eng),
        regions=(reg_hin, reg_eng),
        detection_engine="fasttext-lid",
        model_version="v2.1",
    )

    assert profile.primary_language == "hin"
    assert profile.primary_script == "Deva"
    assert profile.has_multiple_languages() is True

    deva_regions = profile.get_regions_for_script("Deva")
    assert len(deva_regions) == 1
    assert deva_regions[0].language == "hin"

    latn_regions = profile.get_regions_for_script("Latn")
    assert len(latn_regions) == 1
    assert latn_regions[0].language == "eng"

    arab_regions = profile.get_regions_for_script("Arab")
    assert len(arab_regions) == 0


def test_language_detection_profile_immutable_tuples() -> None:
    """Verify profile coerces mutable lists to immutable tuples and resists mutation."""
    id_eng = LanguageScriptIdentification("eng", "Latn", 0.99)
    # Pass list instead of tuple
    profile = LanguageDetectionProfile(
        primary_language="eng",
        primary_script="Latn",
        confidence=0.99,
        detected_languages=[id_eng],  # type: ignore[arg-type]
    )
    assert isinstance(profile.detected_languages, tuple)
    assert len(profile.detected_languages) == 1

    with pytest.raises(FrozenInstanceError):
        profile.primary_language = "fra"  # type: ignore[misc]


def test_language_detection_profile_invalid_raises() -> None:
    """Verify validation errors for bad primary language, script, or confidence."""
    with pytest.raises(ValidationError):
        LanguageDetectionProfile(primary_language="", primary_script="Latn", confidence=0.9)
    with pytest.raises(ValidationError):
        LanguageDetectionProfile(primary_language="eng", primary_script="", confidence=0.9)
    with pytest.raises(ConfidenceRangeError):
        LanguageDetectionProfile(primary_language="eng", primary_script="Latn", confidence=1.5)
