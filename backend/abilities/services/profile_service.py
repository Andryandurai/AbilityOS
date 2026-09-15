"""Business logic for reading and writing an Ability Profile.

Kept out of the view layer (Phase 2 spec section 15) so the same rules —
controlled vocabulary validation, confidence bounds, and "manual beats
inferred beats default" — apply no matter what calls this: the DRF view
today, a future inference pipeline, or a test.
"""

from __future__ import annotations

from abilities.constants import ALLOWED_LEVELS, ALLOWED_SOURCES, MODALITY_VALUES, SOURCE_MANUAL, SOURCE_PRIORITY
from abilities.models import AbilityProfile, default_dimensions


class ProfileValidationError(ValueError):
    """Raised for any ability-profile write that violates the controlled
    vocabulary — an unknown dimension, an out-of-enum level, a
    out-of-range confidence, or an unknown source."""


def get_or_create_profile(user) -> AbilityProfile:
    profile, _ = AbilityProfile.objects.get_or_create(user=user)
    return profile


def validate_dimension_payload(key: str, payload: dict) -> dict:
    """Normalizes and validates one {level, confidence?, source?} entry.
    Raises ProfileValidationError with a message naming the exact problem
    rather than silently coercing or dropping bad data (Phase 2 section 13:
    "Do not silently accept invalid values")."""

    if key not in ALLOWED_LEVELS:
        raise ProfileValidationError(f"Unknown ability dimension '{key}'.")
    if not isinstance(payload, dict) or "level" not in payload:
        raise ProfileValidationError(f"Dimension '{key}' must include a 'level'.")

    level = payload["level"]
    if level not in ALLOWED_LEVELS[key]:
        allowed = ", ".join(ALLOWED_LEVELS[key])
        raise ProfileValidationError(f"Invalid level '{level}' for '{key}'. Allowed values: {allowed}.")

    normalized = {"level": level}

    if "confidence" in payload:
        confidence = payload["confidence"]
        if not isinstance(confidence, (int, float)) or isinstance(confidence, bool):
            raise ProfileValidationError(f"'{key}.confidence' must be a number.")
        if confidence < 0.0 or confidence > 1.0:
            raise ProfileValidationError(f"'{key}.confidence' must be between 0.0 and 1.0, got {confidence}.")
        normalized["confidence"] = float(confidence)

    if "source" in payload:
        source = payload["source"]
        if source not in ALLOWED_SOURCES:
            raise ProfileValidationError(f"Invalid source '{source}' for '{key}'. Allowed: {', '.join(ALLOWED_SOURCES)}.")
        normalized["source"] = source

    return normalized


def apply_manual_update(profile: AbilityProfile, dimensions: dict | None = None, preferred_modality: str | None = None, preferences: dict | None = None) -> AbilityProfile:
    """The one path a person editing their own profile goes through
    (Phase 2 section 8). A PATCH from a real person is, by definition,
    the highest-trust source — it always overwrites whatever was there,
    regardless of that dimension's previous source (Phase 2 section 7:
    manual > inferred > default)."""

    if dimensions:
        if not isinstance(dimensions, dict):
            raise ProfileValidationError("dimensions must be an object.")
        merged = dict(profile.dimensions)
        for key, payload in dimensions.items():
            normalized = validate_dimension_payload(key, payload)
            normalized.setdefault("confidence", 0.95)
            normalized["source"] = SOURCE_MANUAL
            merged[key] = normalized
        profile.dimensions = merged

    if preferred_modality is not None:
        if preferred_modality not in MODALITY_VALUES:
            raise ProfileValidationError(
                f"Invalid preferred_modality '{preferred_modality}'. Allowed: {', '.join(MODALITY_VALUES)}."
            )
        profile.preferred_modality = preferred_modality

    if preferences is not None:
        if not isinstance(preferences, dict):
            raise ProfileValidationError("preferences must be an object.")
        profile.preferences = preferences

    profile.save()
    return profile


def apply_inferred_update(profile: AbilityProfile, key: str, level: str, confidence: float, source: str = "inferred") -> AbilityProfile:
    """The write path a future inference pipeline would use (not exercised
    by any live endpoint in Phase 2 — see docs/ABILITY_PROFILE.md). Proves
    the priority rule holds architecturally: an inferred/session_signal
    value is silently dropped if a manual (or equally-trusted) value is
    already stored for that dimension."""

    if source not in ("inferred", "session_signal"):
        raise ProfileValidationError("apply_inferred_update only accepts source='inferred' or 'session_signal'.")

    normalized = validate_dimension_payload(key, {"level": level, "confidence": confidence, "source": source})

    current = profile.dimensions.get(key, {})
    current_priority = SOURCE_PRIORITY.get(current.get("source"), 0)
    new_priority = SOURCE_PRIORITY.get(source, 0)
    if current_priority > new_priority:
        return profile  # existing higher-trust value wins; write silently skipped

    merged = dict(profile.dimensions)
    merged[key] = normalized
    profile.dimensions = merged
    profile.save(update_fields=["dimensions", "updated_at"])
    return profile


def clear_profile(profile: AbilityProfile) -> AbilityProfile:
    """Phase 2 section 22 ("Clear Profile"): functional values return to
    their defaults; the account itself is untouched."""

    profile.dimensions = default_dimensions()
    profile.preferred_modality = AbilityProfile.MODALITY_VISUAL
    profile.preferences = {}
    profile.save()
    return profile
