"""Structured schemas for the AI Decision Engine's input/output contract.

The LLM response is always validated against `AIDecisionResponse` before any
of it is trusted. A response that fails validation — malformed JSON, an
unknown adaptation id, a barrier_type outside what was asked about — never
reaches the rule engine; it is treated exactly like an AI outage and the
deterministic fallback takes over for that decision.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError

__all__ = ["AIDecision", "AIDecisionResponse", "ValidationError"]


class AIDecision(BaseModel):
    barrier_type: str
    selected_adaptation: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class AIDecisionResponse(BaseModel):
    decisions: list[AIDecision]
