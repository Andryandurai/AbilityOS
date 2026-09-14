from django.db import models


class Adaptation(models.Model):
    """One entry in the fixed, pre-approved catalogue of accessibility actions
    (Part 13). The AI Decision Engine may only choose from this catalogue —
    it never invents a new adaptation (Part 7).
    """

    RISK_LOW = "low"
    RISK_MEDIUM = "medium"
    RISK_HIGH = "high"

    RISK_CHOICES = [
        (RISK_LOW, "Low"),
        (RISK_MEDIUM, "Medium"),
        (RISK_HIGH, "High"),
    ]

    name = models.SlugField(max_length=80, unique=True)
    display_name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    resolves_barrier_types = models.JSONField(
        default=list, help_text="List of barrier_type values this adaptation can resolve."
    )
    modality = models.CharField(
        max_length=20,
        blank=True,
        help_text="Interaction channel this adaptation primarily uses, e.g. 'visual', 'voice', 'haptic'.",
    )
    accessibility_benefit = models.FloatField(help_text="0-1, how directly this resolves a barrier.")
    interaction_cost = models.FloatField(help_text="0-1, how much this changes the interaction.")
    risk = models.FloatField(help_text="0-1, chance this causes a new problem.")
    risk_level = models.CharField(max_length=10, choices=RISK_CHOICES, default=RISK_LOW)
    requires_confirmation = models.BooleanField(default=False)
    allowed_for_tasks = models.JSONField(
        default=list, help_text="Task ids this may be applied to, or ['*'] for all tasks."
    )
    ui_effects = models.JSONField(
        default=dict,
        help_text="Directives the frontend renderer applies, e.g. "
        "{'button_scale': 1.8, 'contrast': 'high', 'flow': 'guided'}.",
    )
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def is_allowed_for_task(self, task_id):
        return "*" in self.allowed_for_tasks or task_id in self.allowed_for_tasks


class AdaptationResult(models.Model):
    """The adaptation selected (and its scoring/rationale) for one barrier
    within a session. A session can have several — one per distinct barrier
    — matching the worked "increase target size + increase contrast" example
    in Part 12/15.
    """

    SOURCE_AI = "ai"
    SOURCE_FALLBACK = "fallback"

    SOURCE_CHOICES = [
        (SOURCE_AI, "AI decision engine"),
        (SOURCE_FALLBACK, "Deterministic fallback"),
    ]

    session = models.ForeignKey(
        "feedback.InteractionSession", on_delete=models.CASCADE, related_name="adaptation_results"
    )
    barrier = models.ForeignKey(
        "barriers.Barrier", on_delete=models.CASCADE, related_name="adaptation_results"
    )
    adaptation = models.ForeignKey(
        Adaptation, on_delete=models.PROTECT, related_name="results"
    )
    score = models.FloatField()
    score_breakdown = models.JSONField(default=dict)
    rationale = models.TextField(blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=SOURCE_FALLBACK)
    candidates_considered = models.JSONField(default=list)
    approved = models.BooleanField(default=False)
    requires_confirmation = models.BooleanField(default=False)
    confirmed = models.BooleanField(default=False)
    applied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-score"]

    def __str__(self):
        return f"AdaptationResult<{self.adaptation.name} for barrier={self.barrier_id}>"
