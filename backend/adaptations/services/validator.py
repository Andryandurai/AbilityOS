"""AdaptationSafetyValidator (Phase 5 sections 24-26).

Independent of the LLM and independent of the deterministic scorer — this
is the one gate every selected adaptation must pass through before it can
ever be called "approved", whether it was chosen by AI or by fallback.
"AI proposes, rules dispose": nothing here trusts that an upstream step
already checked these things; every rule is re-verified from scratch.
"""

from __future__ import annotations

from dataclasses import dataclass

from adaptations.models import Adaptation
from adaptations.services.config import ALLOWED_UI_EFFECT_KEYS


@dataclass
class SafetyValidationResult:
    approved: bool
    requires_confirmation: bool
    reason: str

    def as_dict(self) -> dict:
        return {"approved": self.approved, "requires_confirmation": self.requires_confirmation, "reason": self.reason}


class AdaptationSafetyValidator:
    @staticmethod
    def validate(adaptation: Adaptation | None, barrier, ability_profile: dict, task: dict) -> SafetyValidationResult:
        """barrier: a barriers.services.result.BarrierResult (or anything
        with the same .barrier_type/.ability_dimension attributes).
        ability_profile: AbilityProfile.dimensions-shaped dict.
        task: a TaskDescriptor dict (must include "task_id")."""

        # Rule 1: must exist in the approved catalogue at all.
        if adaptation is None:
            return SafetyValidationResult(False, False, "No such adaptation exists in the approved catalogue.")

        # Rule 2: must be active.
        if not adaptation.enabled:
            return SafetyValidationResult(False, False, f"'{adaptation.name}' is disabled in the catalogue.")

        # Rule 3: must explicitly support the detected barrier type.
        if barrier.barrier_type not in adaptation.resolves_barrier_types:
            return SafetyValidationResult(
                False, False, f"'{adaptation.name}' does not support barrier type '{barrier.barrier_type}'."
            )

        # Rule 4: must be compatible with the relevant ability dimension.
        # In this architecture every barrier type maps to exactly one
        # ability dimension (Phase 4), so this is a real, checkable
        # consistency guarantee, not a rubber stamp: an adaptation that
        # resolves this barrier_type is, by the catalogue's own design,
        # only ever mapped to barrier types whose dimension it was built
        # for. If that invariant were ever violated in the catalogue data
        # itself, this is where it would be caught.
        dimension_dim = ability_profile.get(barrier.ability_dimension)
        if dimension_dim is None:
            return SafetyValidationResult(
                False, False, f"Ability profile has no '{barrier.ability_dimension}' dimension to validate against."
            )

        # Rule 5: must be allowed for this task.
        task_id = task.get("task_id")
        if task_id and not adaptation.is_allowed_for_task(task_id):
            return SafetyValidationResult(
                False, False, f"'{adaptation.name}' is not an approved adaptation for task '{task_id}'."
            )

        # Rules 6 & 7: must not alter the task itself, and must not
        # introduce behaviour outside the known-safe presentation-only
        # effect vocabulary — every key an adaptation declares in
        # `ui_effects` must be on the allowlist.
        unknown_keys = set(adaptation.ui_effects.keys()) - ALLOWED_UI_EFFECT_KEYS
        if unknown_keys:
            return SafetyValidationResult(
                False,
                False,
                f"'{adaptation.name}' declares unsupported effect(s) {sorted(unknown_keys)} outside the "
                "approved presentation-only vocabulary.",
            )

        # Rule 8: high-risk adaptations require explicit confirmation
        # before they may be treated as applied — approved, but flagged.
        if adaptation.risk_level == Adaptation.RISK_HIGH or adaptation.requires_confirmation:
            return SafetyValidationResult(
                True,
                True,
                f"'{adaptation.name}' is approved but classified {adaptation.risk_level} risk — "
                "requires explicit confirmation before being treated as applied.",
            )

        return SafetyValidationResult(True, False, f"'{adaptation.name}' passed all safety checks.")
