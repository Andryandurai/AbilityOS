"""What-If simulation (Phase 7 — Advanced Adaptive Intelligence).

A read-only, side-effect-free re-run of the EXISTING standalone barrier +
adaptation pipeline — the same one `RecommendAdaptationsView._recommend_standalone`
(Phase 3/4/5) already uses for a real profile via `AdaptationRecommender.recommend()`,
which itself already calls `BarrierDetectionService.detect()` internally. No
new barrier engine, no new adaptation engine, no new scoring formula, no
new safety validator — this module only builds a temporarily-modified copy
of the user's real profile dimensions and calls that exact same function
twice (once with the real dimensions, once with the simulated ones).

Nothing here ever writes to `AbilityProfile`, creates an `InteractionSession`,
or persists anything at all — see docs/PHASE_7.md "Side-effect guarantees".
"""

from __future__ import annotations

import copy

from abilities.constants import ALLOWED_LEVELS, DIMENSION_KEYS
from adaptations.services.recommender import AdaptationRecommender


class WhatIfValidationError(ValueError):
    """Raised for an unknown override dimension or an out-of-vocabulary
    value — never a second, ad-hoc ability schema (section 5)."""


def validate_overrides(overrides: dict) -> None:
    if not isinstance(overrides, dict) or not overrides:
        raise WhatIfValidationError("Provide at least one dimension override.")
    for dimension, value in overrides.items():
        if dimension not in DIMENSION_KEYS:
            raise WhatIfValidationError(
                f"Unknown ability dimension '{dimension}'. Allowed: {', '.join(DIMENSION_KEYS)}."
            )
        allowed = ALLOWED_LEVELS[dimension]
        if value not in allowed:
            raise WhatIfValidationError(
                f"Invalid value '{value}' for '{dimension}'. Allowed: {', '.join(allowed)}."
            )


def build_simulated_dimensions(real_dimensions: dict, overrides: dict) -> dict:
    """Returns a new dict — `real_dimensions` (the user's actual, persisted
    AbilityProfile.dimensions) is never mutated. Only `level` changes for an
    overridden dimension; `confidence`/`source` are carried over from the
    real profile unchanged, so the simulation answers "what if this
    dimension's level were different" and nothing else."""

    simulated = copy.deepcopy(real_dimensions)
    for dimension, value in overrides.items():
        current = simulated.get(dimension, {"confidence": 0.5})
        simulated[dimension] = {**current, "level": value}
    return simulated


def _diff(current: dict, simulated: dict) -> dict:
    """Factual, measurable differences only — no "better"/"worse"/"ideal"
    labels (section 6)."""

    current_types = {b["barrier_type"] for b in current["barriers"]}
    simulated_types = {b["barrier_type"] for b in simulated["barriers"]}

    current_selected = current["selected_adaptation"]
    simulated_selected = simulated["selected_adaptation"]
    current_adaptation_id = current_selected["adaptation_id"] if current_selected else None
    simulated_adaptation_id = simulated_selected["adaptation_id"] if simulated_selected else None

    return {
        "barriers_removed": sorted(current_types - simulated_types),
        "barriers_added": sorted(simulated_types - current_types),
        "barrier_count_change": len(simulated_types) - len(current_types),
        "current_adaptation": current_adaptation_id,
        "simulated_adaptation": simulated_adaptation_id,
        "adaptation_changed": current_adaptation_id != simulated_adaptation_id,
    }


def simulate(profile, task_descriptor: dict, environment_descriptor: dict, overrides: dict) -> dict:
    """profile: the user's real abilities.models.AbilityProfile (read-only —
    never saved). task_descriptor/environment_descriptor: the same dict
    shapes tasks.services.task_service / environments.services.analyzer
    already produce for the standalone demo endpoints.

    Runs the existing AdaptationRecommender.recommend() pipeline twice —
    once against the real profile, once against a simulated copy — and
    returns both results plus a factual diff. AI ranking and safety
    validation both run exactly as they do for a real (non-simulated)
    request; nothing about them is aware this is a simulation.
    """

    validate_overrides(overrides)

    real_dimensions = profile.dimensions
    simulated_dimensions = build_simulated_dimensions(real_dimensions, overrides)

    current_result = AdaptationRecommender.recommend(
        real_dimensions, task_descriptor, environment_descriptor, profile.preferred_modality
    )
    simulated_result = AdaptationRecommender.recommend(
        simulated_dimensions, task_descriptor, environment_descriptor, profile.preferred_modality
    )

    return {
        "task_id": task_descriptor.get("task_id"),
        "environment_id": environment_descriptor.get("environment_id"),
        "overrides": overrides,
        "current": {
            "dimensions": real_dimensions,
            "barriers": current_result["barriers"],
            "candidates": current_result["candidates"],
            "selected_adaptation": current_result["selected_adaptation"],
            # AdaptationRecommender.recommend() only includes "reason" when
            # nothing was selected (no barriers / no candidates / no safe
            # adaptation) -- .get() rather than [] since a successful
            # selection's own "reason" already lives inside
            # selected_adaptation.
            "reason": current_result.get("reason"),
        },
        "simulated": {
            "dimensions": simulated_dimensions,
            "barriers": simulated_result["barriers"],
            "candidates": simulated_result["candidates"],
            "selected_adaptation": simulated_result["selected_adaptation"],
            "reason": simulated_result.get("reason"),
        },
        "changes": _diff(current_result, simulated_result),
    }
