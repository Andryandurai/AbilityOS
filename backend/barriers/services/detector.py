"""BarrierDetectionService (Phase 4).

The one entry point Phase 4 exposes: three plain dicts in, a deterministic,
deduplicated, severity-sorted list of BarrierResults out. No database
access, no session — see api/views.py for where those get fetched before
calling this.
"""

from __future__ import annotations

from barriers.services.result import BarrierResult
from barriers.services.rules import BARRIER_RULES


class BarrierDetectionService:
    @staticmethod
    def detect(ability_profile: dict, task: dict, environment: dict) -> list[BarrierResult]:
        """ability_profile: AbilityProfile.dimensions-shaped dict.
        task: a TaskDescriptor dict (tasks.services.task_service).
        environment: an EnvironmentDescriptor dict
        (environments.services.analyzer.EnvironmentAnalyzer)."""

        results: list[BarrierResult] = []
        for rule in BARRIER_RULES:
            results.extend(rule.detect(ability_profile, task, environment))

        # Exact-duplicate guard: no rule currently can fire twice for the
        # same (barrier_type, ability_dimension) pair, but this keeps the
        # contract explicit rather than assuming it can never happen.
        seen = set()
        deduped = []
        for result in results:
            key = (result.barrier_type, result.ability_dimension)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(result)

        deduped.sort(key=lambda r: r.severity, reverse=True)
        return deduped
