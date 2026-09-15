"""AdaptationCatalogueService (Phase 5 section 9).

A thin, named service wrapping the existing `Adaptation` model (built and
seeded in an earlier pass on this repo, already powering the real kiosk
demo) — the AI Decision Engine and the recommender always go through this,
never query `Adaptation` directly, so "only approved, active adaptations
are ever offered as candidates" holds in one place.
"""

from __future__ import annotations

from adaptations.models import Adaptation


class AdaptationCatalogueService:
    @staticmethod
    def get_all_active() -> list[Adaptation]:
        return list(Adaptation.objects.filter(enabled=True))

    @staticmethod
    def get_for_barrier(barrier_type: str, task_id: str | None = None) -> list[Adaptation]:
        """Only adaptations that explicitly declare they resolve this exact
        barrier type (Phase 5 section 8: "mappings must be explicit") —
        never every adaptation, never a fuzzy match."""

        candidates = [a for a in AdaptationCatalogueService.get_all_active() if barrier_type in a.resolves_barrier_types]
        if task_id is not None:
            candidates = [a for a in candidates if a.is_allowed_for_task(task_id)]
        return candidates

    @staticmethod
    def get_by_id(adaptation_id: str) -> Adaptation | None:
        return Adaptation.objects.filter(name=adaptation_id, enabled=True).first()
