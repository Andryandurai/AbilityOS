"""Safety rule validation (Part 7, Part 13, Part 26).

"LLM proposes, rule engine disposes." Every adaptation — whether chosen by
the AI Decision Engine or the deterministic fallback — passes through here
before it is marked approved. The rule engine never trusts the AI's choice
blindly: it re-checks the adaptation is enabled, is allowed for this task,
and flags high-risk adaptations for explicit confirmation rather than
silently auto-applying them.
"""

from __future__ import annotations

from dataclasses import dataclass

from adaptations.models import Adaptation


@dataclass
class ValidationResult:
    approved: bool
    requires_confirmation: bool
    reason: str


def validate_adaptation(adaptation: Adaptation, task_id: str) -> ValidationResult:
    if not adaptation.enabled:
        return ValidationResult(False, False, f"'{adaptation.name}' is disabled in the catalogue.")

    if not adaptation.is_allowed_for_task(task_id):
        return ValidationResult(
            False, False, f"'{adaptation.name}' is not an approved adaptation for task '{task_id}'."
        )

    if adaptation.risk_level == Adaptation.RISK_HIGH or adaptation.requires_confirmation:
        return ValidationResult(
            True,
            True,
            f"'{adaptation.name}' is approved but classified {adaptation.risk_level} risk — "
            "presenting for explicit confirmation before it is applied.",
        )

    return ValidationResult(True, False, f"'{adaptation.name}' passed safety validation.")
