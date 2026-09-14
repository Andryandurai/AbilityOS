from django.db import models


class Task(models.Model):
    """Registry entry for a task AbilityOS knows how to adapt (Part 5/9).

    The task itself never changes — only how it is presented. `task_id` is
    the stable slug apps/kiosks declare (e.g. "purchase_ticket").
    """

    task_id = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.task_id


class TaskStep(models.Model):
    """One step of a task, and the controls a person must operate to clear it."""

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="steps")
    order = models.PositiveIntegerField()
    step_id = models.SlugField(max_length=80)
    name = models.CharField(max_length=120)
    controls = models.JSONField(
        default=list,
        help_text="List of control descriptors, e.g. "
        "[{'id': 'buy_ticket', 'type': 'button', 'label': 'Buy Ticket'}]",
    )

    class Meta:
        ordering = ["task", "order"]
        unique_together = [("task", "step_id")]

    def __str__(self):
        return f"{self.task.task_id}:{self.step_id}"
