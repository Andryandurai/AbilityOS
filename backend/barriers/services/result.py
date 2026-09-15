"""The Barrier Detection Engine's output shape (Phase 4).

A BarrierResult describes a mismatch — never a fix. It deliberately has no
`adaptation`/`recommended_action`/`solution` field; choosing what to do
about a barrier is a later phase's job, not this one's.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from barriers.services.config import clamp


@dataclass
class BarrierResult:
    barrier_type: str
    ability_dimension: str
    severity: float
    confidence: float
    title: str
    description: str
    evidence: dict = field(default_factory=dict)

    def __post_init__(self):
        # Severity/confidence are always meaningful numbers in [0, 1],
        # never something a caller has to trust was clamped upstream.
        self.severity = round(clamp(self.severity), 3)
        self.confidence = round(clamp(self.confidence), 3)

    def as_dict(self) -> dict:
        return {
            "barrier_type": self.barrier_type,
            "ability_dimension": self.ability_dimension,
            "severity": self.severity,
            "confidence": self.confidence,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
        }
