"""Deterministic fallback path for the AI Decision Engine.

Used whenever AI is not configured, the provider call fails, or the AI's
response doesn't validate. This is a legitimate decision path in its own
right (Part 12's scoring formula), not a degraded stub — the demo must
never break because an external API is unavailable (Part 10/Part 41).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from adaptations.services.scoring import ScoredCandidate, rank_candidates_for_barrier


@dataclass
class Decision:
    barrier: object
    adaptation: object | None
    score: float
    breakdown: dict
    rationale: str
    source: str
    ai_confidence: float | None
    candidates_considered: list = field(default_factory=list)


def decide_fallback(barrier, task_id: str, preferred_modality: str) -> Decision | None:
    ranked: list[ScoredCandidate] = rank_candidates_for_barrier(barrier, task_id, preferred_modality)
    if not ranked:
        return None
    top = ranked[0]
    return Decision(
        barrier=barrier,
        adaptation=top.adaptation,
        score=top.score,
        breakdown=top.as_dict()["breakdown"],
        rationale=(
            f"Deterministic fallback: '{top.adaptation.display_name}' scored highest "
            f"({top.score:.2f}) using Accessibility Benefit + Task Relevance + User "
            f"Preference + Confidence − Interaction Cost − Risk."
        ),
        source="fallback",
        ai_confidence=None,
        candidates_considered=[c.as_dict() for c in ranked],
    )
