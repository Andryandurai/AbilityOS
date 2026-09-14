"""Deterministic adaptation scoring (Part 12 — the Adaptation Engine).

    Adaptation Score = Accessibility Benefit + Task Relevance + User
                        Preference + Confidence - Interaction Cost - Risk

This module answers the project's central question for one barrier at a
time: given a detected barrier, what is the smallest useful intervention?
It is deliberately conservative — the highest-scoring candidate is usually
the cheapest one that clears the barrier, not the most powerful one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from adaptations.models import Adaptation


@dataclass
class ScoredCandidate:
    adaptation: Adaptation
    accessibility_benefit: float
    task_relevance: float
    user_preference: float
    confidence: float
    interaction_cost: float
    risk: float
    score: float = field(init=False)

    def __post_init__(self):
        self.score = round(
            self.accessibility_benefit
            + self.task_relevance
            + self.user_preference
            + self.confidence
            - self.interaction_cost
            - self.risk,
            4,
        )

    def as_dict(self) -> dict:
        return {
            "adaptation": self.adaptation.name,
            "display_name": self.adaptation.display_name,
            "score": self.score,
            "breakdown": {
                "accessibility_benefit": round(self.accessibility_benefit, 3),
                "task_relevance": round(self.task_relevance, 3),
                "user_preference": round(self.user_preference, 3),
                "confidence": round(self.confidence, 3),
                "interaction_cost": round(self.interaction_cost, 3),
                "risk": round(self.risk, 3),
            },
            "risk_level": self.adaptation.risk_level,
        }


def _modality_matches(adaptation: Adaptation, preferred_modality: str) -> bool:
    if not adaptation.modality or not preferred_modality:
        return False
    return adaptation.modality in preferred_modality or preferred_modality in adaptation.modality


def candidates_for_barrier(barrier_type: str, task_id: str) -> list[Adaptation]:
    """All enabled, task-allowed adaptations that can resolve this barrier type."""

    return [
        a
        for a in Adaptation.objects.filter(enabled=True)
        if barrier_type in a.resolves_barrier_types and a.is_allowed_for_task(task_id)
    ]


def score_candidate(adaptation: Adaptation, barrier, task_id: str, preferred_modality: str) -> ScoredCandidate:
    benefit = adaptation.accessibility_benefit * (0.5 + 0.5 * barrier.severity)
    task_relevance = 1.0 if adaptation.is_allowed_for_task(task_id) else 0.0
    user_preference = 0.2 if _modality_matches(adaptation, preferred_modality) else 0.0
    confidence = barrier.confidence
    return ScoredCandidate(
        adaptation=adaptation,
        accessibility_benefit=benefit,
        task_relevance=task_relevance,
        user_preference=user_preference,
        confidence=confidence,
        interaction_cost=adaptation.interaction_cost,
        risk=adaptation.risk,
    )


def rank_candidates_for_barrier(barrier, task_id: str, preferred_modality: str) -> list[ScoredCandidate]:
    candidates = candidates_for_barrier(barrier.barrier_type, task_id)
    scored = [score_candidate(a, barrier, task_id, preferred_modality) for a in candidates]
    scored.sort(key=lambda c: c.score, reverse=True)
    return scored
