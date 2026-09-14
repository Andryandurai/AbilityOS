from django.db import models


class Barrier(models.Model):
    """A detected mismatch between ability, task and environment (Part 3/6).

    Produced deterministically by barriers.services.detection — the LLM is
    never used for this step; a barrier is either present by the rules or
    it isn't.
    """

    TYPE_SMALL_TAP_TARGETS = "small_tap_targets"
    TYPE_LOW_CONTRAST = "low_contrast"
    TYPE_TOO_MANY_CHOICES = "too_many_choices"
    TYPE_AUDIO_ONLY_ALERT = "audio_only_alert"
    TYPE_FATIGUE_DEGRADED_PRECISION = "fatigue_degraded_precision"

    TYPE_CHOICES = [
        (TYPE_SMALL_TAP_TARGETS, "Small tap targets"),
        (TYPE_LOW_CONTRAST, "Low contrast / small text"),
        (TYPE_TOO_MANY_CHOICES, "Too many simultaneous choices"),
        (TYPE_AUDIO_ONLY_ALERT, "Audio-only alert"),
        (TYPE_FATIGUE_DEGRADED_PRECISION, "Fatigue-degraded precision"),
    ]

    session = models.ForeignKey(
        "feedback.InteractionSession", on_delete=models.CASCADE, related_name="barriers"
    )
    barrier_type = models.CharField(max_length=60, choices=TYPE_CHOICES)
    ability_dimension = models.CharField(max_length=40)
    severity = models.FloatField(help_text="0 (negligible) - 1 (severe).")
    confidence = models.FloatField(help_text="Confidence in the underlying ability signal.")
    evidence = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-severity"]

    def __str__(self):
        return f"Barrier<{self.barrier_type} severity={self.severity:.2f}>"
