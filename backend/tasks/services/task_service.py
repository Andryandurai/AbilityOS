"""Task Understanding Engine (Phase 3).

Converts a `task_id` into a structured TaskDescriptor. Deterministic by
design: a plain database lookup keyed on an exact slug, never an LLM call
or fuzzy match — see docs/PHASE_3.md for why. This module answers "what is
the person trying to accomplish, and what does that involve?" only. It
never compares that against an Ability Profile or an environment — that
comparison is Phase 4's job (Barrier Detection), not this one's.
"""

from __future__ import annotations

from tasks.models import Task


class TaskNotFoundError(LookupError):
    """Raised for an unknown task_id — the caller should turn this into an
    HTTP 404, never silently invent a task."""


def get_task_descriptor(task_id: str) -> dict:
    """Returns the TaskDescriptor dict for `task_id`. Raises
    TaskNotFoundError if no such task is registered — Phase 3 never
    silently creates an unknown task."""

    if not task_id:
        raise TaskNotFoundError("task_id is required.")

    try:
        task = Task.objects.prefetch_related("steps").get(task_id=task_id)
    except Task.DoesNotExist as exc:
        raise TaskNotFoundError(f"Unknown task_id '{task_id}'.") from exc

    steps = list(task.steps.all().order_by("order"))

    all_controls = []
    seen_ids = set()
    for step in steps:
        for control in step.controls:
            if control.get("id") in seen_ids:
                continue
            seen_ids.add(control.get("id"))
            all_controls.append(control)

    return {
        "task_id": task.task_id,
        "name": task.name,
        "description": task.description,
        "steps": [
            {
                "id": step.step_id,
                "order": step.order,
                "name": step.name,
                "description": step.description,
                "required": step.required,
                "controls": step.controls,
            }
            for step in steps
        ],
        "controls": all_controls,
        "time_limit_seconds": task.time_limit_seconds,
    }
