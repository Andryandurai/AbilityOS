from django.db import models


class Task(models.Model):
    """Registry entry for a task AbilityOS knows how to adapt (Part 5/9).

    The task itself never changes — only how it is presented. `task_id` is
    the stable slug apps/kiosks declare (e.g. "purchase_ticket"). Backed by
    the database rather than an in-memory registry (Phase 1's architecture
    choice) — `tasks.services.task_service` is the thin, deterministic
    lookup layer other code should go through instead of querying this
    model directly, so "no LLM, no fuzzy matching, just an exact task_id
    lookup" stays true in one place.
    """

    task_id = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    time_limit_seconds = models.PositiveIntegerField(
        null=True, blank=True, help_text="Optional overall time limit for the task, if any."
    )

    def __str__(self):
        return self.task_id


class TaskStep(models.Model):
    """One step of a task, and the controls a person must operate to clear it.

    This is a fact about the task, not an accessibility judgement — Phase 3
    describes what the step requires; Phase 4 is the only place that gets
    to decide whether a given person can do it comfortably.
    """

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveIntegerField()
    step_id = models.SlugField(max_length=80)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    required = models.BooleanField(default=True)
    controls = models.JSONField(
        default=list,
        help_text="List of control descriptors, e.g. "
        "[{'id': 'buy_ticket', 'type': 'button', 'label': 'Buy Ticket', 'interaction_type': 'touch'}]",
    )

    class Meta:
        ordering = ["task", "order"]
        unique_together = [("task", "step_id")]

    def __str__(self):
        return f"{self.task.task_id}:{self.step_id}"
