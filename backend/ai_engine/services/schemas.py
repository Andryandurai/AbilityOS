"""Structured schemas for the AI Decision Engine's input/output contract.

The LLM response is always validated against `AIDecisionResponse` before any
of it is trusted. A response that fails validation — malformed JSON, an
unknown adaptation id, a barrier_type outside what was asked about — never
reaches the rule engine; it is treated exactly like an AI outage and the
deterministic fallback takes over for that decision.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError

__all__ = [
    "AIDecision",
    "AIDecisionResponse",
    "AdaptationRanking",
    "AdaptationRecommendationResponse",
    "ValidationError",
]


class AIDecision(BaseModel):
    barrier_type: str
    selected_adaptation: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class AIDecisionResponse(BaseModel):
    decisions: list[AIDecision]


# --- Phase 5: single-recommendation contract (adaptations/services/recommender.py) ---
# A separate schema from AIDecisionResponse above (which decides one
# adaptation per barrier, independently) — this one ranks the *entire*
# candidate pool across all detected barriers and names one overall winner,
# matching the "select ONE primary adaptation" MVP scope (Phase 5 section 28).
class AdaptationRanking(BaseModel):
    adaptation_id: str
    rank: int = Field(ge=1)
    rationale: str = Field(min_length=1, max_length=400)


class AdaptationRecommendationResponse(BaseModel):
    selected_adaptation_id: str
    ranked_adaptations: list[AdaptationRanking]
    overall_rationale: str = Field(min_length=1, max_length=600)
