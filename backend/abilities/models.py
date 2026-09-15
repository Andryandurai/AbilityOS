from django.conf import settings
from django.db import models

from abilities.constants import ALLOWED_SOURCES, DEFAULT_LEVEL, DIMENSION_KEYS, SOURCE_DEFAULT, SOURCE_MANUAL

__all__ = ["AbilityProfile", "DIMENSION_KEYS", "default_dimensions"]


def default_dimensions():
    """Every dimension's own "no barrier" baseline — not a single shared
    value, since some dimensions (reach, fatigue) don't have "typical" in
    their controlled vocabulary at all (Phase 2 spec section 4)."""

    return {
        key: {"level": DEFAULT_LEVEL[key], "confidence": 0.5, "source": SOURCE_DEFAULT}
        for key in DIMENSION_KEYS
    }


class AbilityProfile(models.Model):
    """The functional, non-diagnostic Ability Profile at the centre of AbilityOS.

    AbilityOS never tries to determine what condition a person has — only
    functional questions about the here-and-now interaction (Part 3/4).
    """

    MODALITY_VISUAL = "visual"
    MODALITY_VOICE = "voice"
    MODALITY_HAPTIC = "haptic"
    MODALITY_MIXED = "mixed"

    MODALITY_CHOICES = [
        (MODALITY_VISUAL, "Visual"),
        (MODALITY_VOICE, "Voice"),
        (MODALITY_HAPTIC, "Haptic"),
        (MODALITY_MIXED, "Mixed (visual + haptic)"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ability_profile"
    )
    label = models.CharField(
        max_length=120,
        blank=True,
        help_text="Human-friendly name for demo/selection purposes, e.g. 'Low Vision + Reduced Dexterity'.",
    )
    dimensions = models.JSONField(default=default_dimensions)
    preferred_modality = models.CharField(
        max_length=20, choices=MODALITY_CHOICES, default=MODALITY_VISUAL
    )
    preferences = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.label or f"AbilityProfile<{self.user.username}>"

    def dimension(self, key, default=None):
        if default is not None:
            return self.dimensions.get(key, default)
        fallback = {"level": DEFAULT_LEVEL.get(key, "typical"), "confidence": 0.5, "source": SOURCE_DEFAULT}
        return self.dimensions.get(key, fallback)

    def set_dimension(self, key, level, confidence=0.7, source=SOURCE_MANUAL):
        """Low-level setter used by tests/services that have already
        validated `level`/`source` against abilities.constants — prefer
        abilities.services.profile_service for anything reachable from an
        API request, since that layer enforces the controlled vocabulary."""

        if key not in DIMENSION_KEYS:
            raise ValueError(f"Unknown ability dimension: {key}")
        if source not in ALLOWED_SOURCES:
            raise ValueError(f"Unknown source: {source}")
        dims = dict(self.dimensions)
        dims[key] = {"level": level, "confidence": confidence, "source": source}
        self.dimensions = dims

    def update_dimension_confidence(self, key, delta):
        """Learning-loop hook (Part 3 / Part 5 step 12): nudge confidence
        for a dimension after feedback confirms or contradicts it."""
        if key not in self.dimensions:
            return
        dim = dict(self.dimensions[key])
        dim["confidence"] = max(0.0, min(1.0, dim.get("confidence", 0.5) + delta))
        dims = dict(self.dimensions)
        dims[key] = dim
        self.dimensions = dims
