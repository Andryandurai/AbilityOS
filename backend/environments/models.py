from django.db import models


class Environment(models.Model):
    """A captured description of a screen/physical context (Part 5/14).

    For the hackathon MVP this is backed by a JSON fixture describing the
    simulated kiosk (control sizes, contrast, choice count, audio alerts).
    Optional computer-vision analysis of a real screenshot can populate the
    same `data` shape — see ai_engine.services.vision_service.
    """

    SOURCE_FIXTURE = "fixture"
    SOURCE_VISION = "vision"

    SOURCE_CHOICES = [
        (SOURCE_FIXTURE, "JSON fixture"),
        (SOURCE_VISION, "Computer vision analysis"),
    ]

    environment_id = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_FIXTURE)
    data = models.JSONField(
        default=dict,
        help_text="Screen/control layout: controls, contrast, visible_choice_count, "
        "audio_alert, noise_level, screen dimensions.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.environment_id
