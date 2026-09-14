from django.conf import settings
from django.db import models


class InteractionSession(models.Model):
    """One person-task-environment interaction (Part 5, Part 10).

    This is the row that ties together the user, the task, the environment,
    the barriers detected, the adaptation(s) chosen, and the eventual
    feedback — the same row the analytics module aggregates over.
    """

    STATUS_STARTED = "started"
    STATUS_ANALYZED = "analyzed"
    STATUS_ADAPTED = "adapted"
    STATUS_COMPLETED = "completed"
    STATUS_ABANDONED = "abandoned"

    STATUS_CHOICES = [
        (STATUS_STARTED, "Started"),
        (STATUS_ANALYZED, "Analyzed"),
        (STATUS_ADAPTED, "Adapted"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_ABANDONED, "Abandoned"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interaction_sessions"
    )
    task = models.ForeignKey("tasks.Task", on_delete=models.CASCADE, related_name="sessions")
    environment = models.ForeignKey(
        "environments.Environment", on_delete=models.SET_NULL, null=True, related_name="sessions"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_STARTED)
    ai_used = models.BooleanField(default=False)
    baseline_mode = models.BooleanField(
        default=False,
        help_text="True = barriers are detected but no adaptation is applied, so this "
        "session can feed the 'without AbilityOS' side of the before/after metrics.",
    )
    is_seed = models.BooleanField(
        default=False, help_text="True for demo data created by seed_demo, not a live session."
    )
    ability_profile_snapshot = models.JSONField(
        default=dict, help_text="Copy of AbilityProfile.dimensions at session start, for audit."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Session#{self.pk} {self.user} / {self.task.task_id} [{self.status}]"


class Feedback(models.Model):
    """Outcome metrics for a session (Part 5 step 11, Part 18/20)."""

    session = models.OneToOneField(
        InteractionSession, on_delete=models.CASCADE, related_name="feedback"
    )
    completed = models.BooleanField(default=False)
    errors = models.PositiveIntegerField(default=0)
    time_seconds = models.PositiveIntegerField(default=0)
    assistance_requested = models.BooleanField(default=False)
    effort = models.PositiveSmallIntegerField(
        default=3, help_text="Self-reported effort, 1 (low) - 5 (high)."
    )
    confidence = models.PositiveSmallIntegerField(
        default=3, help_text="Self-reported confidence, 1 (low) - 5 (high)."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback<session={self.session_id} completed={self.completed}>"
