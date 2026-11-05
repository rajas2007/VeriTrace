"""Serialization and conversion helpers for persistence mappers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from veritrace.domain.value_objects.geometry import NormalizedBoundingBox
from veritrace.domain.value_objects.multilingual import (
    LanguageDetectionProfile,
    LanguageScriptIdentification,
    LanguageScriptRegion,
)


def bbox_to_dict(bbox: NormalizedBoundingBox | None) -> dict[str, float] | None:
    """Serialize a NormalizedBoundingBox value object to a JSON-compatible dictionary."""
    if bbox is None:
        return None
    return {
        "ymin": float(bbox.ymin),
        "xmin": float(bbox.xmin),
        "ymax": float(bbox.ymax),
        "xmax": float(bbox.xmax),
    }


def dict_to_bbox(data: Any) -> NormalizedBoundingBox | None:
    """Deserialize a JSON dictionary or 4-element list into a NormalizedBoundingBox."""
    if data is None:
        return None
    if isinstance(data, (list, tuple)) and len(data) == 4:
        return NormalizedBoundingBox(
            ymin=float(data[0]),
            xmin=float(data[1]),
            ymax=float(data[2]),
            xmax=float(data[3]),
        )
    if isinstance(data, dict):
        return NormalizedBoundingBox(
            ymin=float(data["ymin"]),
            xmin=float(data["xmin"]),
            ymax=float(data["ymax"]),
            xmax=float(data["xmax"]),
        )
    return None


def language_profile_to_dict(
    profile: LanguageDetectionProfile | None,
) -> dict[str, Any] | None:
    """Serialize LanguageDetectionProfile to a JSON-compatible dictionary."""
    if profile is None:
        return None
    return {
        "primary_language": profile.primary_language,
        "primary_script": profile.primary_script,
        "confidence": profile.confidence,
        "detection_engine": profile.detection_engine,
        "model_version": profile.model_version,
        "detected_languages": [
            {
                "language": lang.language,
                "script": lang.script,
                "confidence": lang.confidence,
            }
            for lang in profile.detected_languages
        ],
        "regions": [
            {
                "language": reg.language,
                "script": reg.script,
                "confidence": reg.confidence,
                "normalized_bbox": reg.normalized_bbox.as_list(),
            }
            for reg in profile.regions
        ],
    }


def dict_to_language_profile(
    data: dict[str, Any] | None,
) -> LanguageDetectionProfile | None:
    """Deserialize a JSON dictionary into a LanguageDetectionProfile value object."""
    if not data:
        return None

    detected = tuple(
        LanguageScriptIdentification(
            language=item["language"],
            script=item["script"],
            confidence=float(item["confidence"]),
        )
        for item in data.get("detected_languages", [])
    )

    regions_list = []
    for reg in data.get("regions", []):
        raw_bbox = reg.get("normalized_bbox")
        bbox = dict_to_bbox(raw_bbox)
        if bbox is not None:
            regions_list.append(
                LanguageScriptRegion(
                    language=reg["language"],
                    script=reg["script"],
                    confidence=float(reg["confidence"]),
                    normalized_bbox=bbox,
                )
            )

    return LanguageDetectionProfile(
        primary_language=data["primary_language"],
        primary_script=data["primary_script"],
        confidence=float(data["confidence"]),
        detected_languages=detected,
        regions=tuple(regions_list),
        detection_engine=data.get("detection_engine", "fasttext-lid"),
        model_version=data.get("model_version"),
    )


def to_utc(dt: datetime | None) -> datetime | None:
    """Ensure datetime is in UTC timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
