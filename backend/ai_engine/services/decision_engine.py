"""AI Decision Engine orchestration (Part 6 Module 6, Part 7, Part 9).

For each detected barrier, ranks candidate adaptations deterministically,
then — if an AI provider is configured — asks the LLM to weigh in on which
candidate to pick and why, always re-validating that choice against the
supplied candidate list. Anything the LLM gets wrong (unknown adaptation,
malformed JSON, missing decision) falls back to the deterministic top-score
pick for that one barrier only, so a partially-bad AI response doesn't
sink the whole session.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from adaptations.services.scoring import rank_candidates_for_barrier
from ai_engine.services import llm_client, prompts
from ai_engine.services.fallback import Decision, decide_fallback
from ai_engine.services.schemas import AIDecisionResponse, ValidationError

logger = logging.getLogger("ai_engine")


@dataclass
class DecisionOutcome:
    decisions: list[Decision]
    ai_used: bool
    ai_error: str | None = None


def _task_descriptor_payload(task) -> dict:
    return {
        "task_id": task.task_id,
        "name": task.name,
        "steps": [s.step_id for s in task.steps.all().order_by("order")],
    }


def decide(barriers, task, profile) -> DecisionOutcome:
    """barriers: iterable of barriers.models.Barrier (already persisted).
    task: tasks.models.Task. profile: abilities.models.AbilityProfile.
    """

    ranked_by_barrier = {}
    for barrier in barriers:
        ranked = rank_candidates_for_barrier(barrier, task.task_id, profile.preferred_modality)
        if ranked:
            ranked_by_barrier[barrier.id] = (barrier, ranked)

    if not ranked_by_barrier:
        return DecisionOutcome(decisions=[], ai_used=False, ai_error=None)

    if not llm_client.is_configured():
        decisions = [
            decide_fallback(barrier, task.task_id, profile.preferred_modality)
            for barrier, _ in ranked_by_barrier.values()
        ]
        return DecisionOutcome(decisions=[d for d in decisions if d], ai_used=False, ai_error=None)

    return _decide_with_ai(ranked_by_barrier, task, profile)


def _decide_with_ai(ranked_by_barrier: dict, task, profile) -> DecisionOutcome:
    barriers_payload = []
    for barrier, ranked in ranked_by_barrier.values():
        barriers_payload.append(
            {
                "barrier_type": barrier.barrier_type,
                "ability_dimension": barrier.ability_dimension,
                "severity": round(barrier.severity, 3),
                "evidence": barrier.evidence,
                "candidates": [
                    {
                        "id": c.adaptation.name,
                        "display_name": c.adaptation.display_name,
                        "deterministic_score": c.score,
                        "accessibility_benefit": round(c.accessibility_benefit, 3),
                        "interaction_cost": round(c.interaction_cost, 3),
                        "risk": round(c.risk, 3),
                    }
                    for c in ranked
                ],
            }
        )

    # Only confirmed profile fields relevant to the detected barriers are
    # shared — never the whole profile, never free text about the person.
    relevant_dims = {b.ability_dimension for b, _ in ranked_by_barrier.values()}
    profile_payload = {
        dim: profile.dimensions.get(dim) for dim in relevant_dims if dim in profile.dimensions
    }

    task_descriptor = _task_descriptor_payload(task)
    task_descriptor["relevant_ability_profile"] = profile_payload

    user_prompt = prompts.build_user_prompt(task_descriptor, barriers_payload)

    try:
        raw = llm_client.call(prompts.SYSTEM_PROMPT, user_prompt)
        parsed = AIDecisionResponse.model_validate(json.loads(raw))
    except (llm_client.LLMUnavailableError, json.JSONDecodeError, ValidationError) as exc:
        logger.warning("AI decision unavailable/invalid, using full fallback: %s", exc)
        decisions = [
            decide_fallback(barrier, task.task_id, profile.preferred_modality)
            for barrier, _ in ranked_by_barrier.values()
        ]
        return DecisionOutcome(
            decisions=[d for d in decisions if d], ai_used=False, ai_error=str(exc)
        )

    by_barrier_type = {d.barrier_type: d for d in parsed.decisions}
    decisions: list[Decision] = []
    any_ai_used = False

    for barrier, ranked in ranked_by_barrier.values():
        ai_decision = by_barrier_type.get(barrier.barrier_type)
        candidate_ids = {c.adaptation.name for c in ranked}
        candidate_by_id = {c.adaptation.name: c for c in ranked}

        if ai_decision and ai_decision.selected_adaptation in candidate_ids:
            chosen = candidate_by_id[ai_decision.selected_adaptation]
            decisions.append(
                Decision(
                    barrier=barrier,
                    adaptation=chosen.adaptation,
                    score=chosen.score,
                    breakdown=chosen.as_dict()["breakdown"],
                    rationale=ai_decision.rationale,
                    source="ai",
                    ai_confidence=ai_decision.confidence,
                    candidates_considered=[c.as_dict() for c in ranked],
                )
            )
            any_ai_used = True
        else:
            if ai_decision:
                logger.warning(
                    "AI selected unknown adaptation '%s' for barrier '%s' — falling back.",
                    ai_decision.selected_adaptation,
                    barrier.barrier_type,
                )
            fb = decide_fallback(barrier, task.task_id, profile.preferred_modality)
            if fb:
                decisions.append(fb)

    return DecisionOutcome(decisions=decisions, ai_used=any_ai_used, ai_error=None)
