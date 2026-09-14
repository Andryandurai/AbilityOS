from django.conf import settings
from django.db import models

# The ten functional dimensions from Part 4 of the AbilityOS spec. Each is
# stored as {"level": str, "confidence": float, "source": str} inside the
# `dimensions` JSONField below — a deliberate, spec-sanctioned shortcut
# ("...or as a JSON field on the user profile for speed") that keeps the
# schema flexible without inventing a diagnosis system.
DIMENSION_KEYS = [
    "vision",
    "hearing",
    "dexterity",
    "reach",
    "mobility",
    "speech",
    "cognition",
    "fatigue",
    "reaction_speed",
]

SOURCE_MANUAL = "manual"
SOURCE_INFERRED = "inferred"
SOURCE_DEFAULT = "default"
SOURCE_SESSION_SIGNAL = "session_signal"

DEFAULT_DIMENSION = {"level": "typical", "confidence": 0.5, "source": SOURCE_DEFAULT}


def default_dimensions():
    return {key: dict(DEFAULT_DIMENSION) for key in DIMENSION_KEYS}


class AbilityProfile(models.Model):
    """The functional, non-diagnostic Ability Profile at the centre of AbilityOS.

    AbilityOS never tries to determine what condition a person has — only
    functional questions about the here-and-now interaction (Part 3/4).
    """

    MODALITY_VISUAL = "visual"
    MODALITY_VOICE = "voice"
    MODALITY_HAPTIC = "haptic"
    MODALITY_MIXED = "visual+haptic"

    MODALITY_CHOICES = [
        (MODALITY_VISUAL, "Visual"),
        (MODALITY_VOICE, "Voice"),
        (MODALITY_HAPTIC, "Haptic"),
        (MODALITY_MIXED, "Visual + Haptic"),
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
        return self.dimensions.get(key, default or dict(DEFAULT_DIMENSION))

    def set_dimension(self, key, level, confidence=0.7, source=SOURCE_MANUAL):
        if key not in DIMENSION_KEYS:
            raise ValueError(f"Unknown ability dimension: {key}")
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
