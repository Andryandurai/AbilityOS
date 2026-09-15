"""AdaptationRecommender (Phase 5) — the standalone recommendation pipeline.

    List[Barrier] -> candidate adaptations -> deterministic scoring
                  -> AI ranking (optional) -> safety validation
                  -> ApprovedAdaptation

Mirrors the architecture of Phase 3/4's standalone endpoints: reuses the
already-approved, already-tested deterministic scoring
(adaptations.services.scoring) and AI plumbing (ai_engine.services.llm_client)
unchanged, adds only the new orchestration this phase's single-selection
contract needs. Does not persist anything — a stateless "what would be
recommended" query, same pattern as the Phase 3/4 analyze endpoints.
"""

from __future__ import annotations

import json
import logging

from adaptations.services.catalogue import AdaptationCatalogueService  # noqa: F401 (documents the intended entry point)
from adaptations.services.scoring import rank_candidates_for_barrier
from adaptations.services.validator import AdaptationSafetyValidator
from ai_engine.services import llm_client
from ai_engine.services.prompts import RECOMMENDER_SYSTEM_PROMPT, build_recommender_prompt
from ai_engine.services.schemas import AdaptationRecommendationResponse, ValidationError
from barriers.services.detector import BarrierDetectionService

logger = logging.getLogger("adaptations")

NO_BARRIERS_REASON = "No accessibility mismatch detected."
NO_CANDIDATES_REASON = "No approved adaptation is available for the detected barrier(s)."
NO_SAFE_ADAPTATION = "no_safe_adaptation"


class AdaptationRecommender:
    @staticmethod
    def recommend(ability_profile: dict, task: dict, environment: dict, preferred_modality: str) -> dict:
        """ability_profile: AbilityProfile.dimensions-shaped dict.
        task: a TaskDescriptor dict (tasks.services.task_service).
        environment: an EnvironmentDescriptor dict (environments.services.analyzer).
        preferred_modality: AbilityProfile.preferred_modality string.
        """

        barriers = BarrierDetectionService.detect(ability_profile, task, environment)

        if not barriers:
            # No LLM call needed — nothing to reason about (Phase 5 section 52).
            return {"barriers": [], "candidates": [], "selected_adaptation": None, "reason": NO_BARRIERS_REASON}

        task_id = task.get("task_id")
        pool: dict[str, dict] = {}
        per_barrier_ranked: dict[str, list] = {}

        for barrier in barriers:
            ranked = rank_candidates_for_barrier(barrier, task_id, preferred_modality)
            per_barrier_ranked[barrier.barrier_type] = ranked
            for scored in ranked:
                key = scored.adaptation.name
                entry = pool.get(key)
                if entry is None or scored.score > entry["score_entry"].score:
                    pool[key] = {"adaptation": scored.adaptation, "score_entry": scored, "barrier_types": set()}
                pool[key]["barrier_types"].add(barrier.barrier_type)

        barriers_payload = [b.as_dict() for b in barriers]

        if not pool:
            return {
                "barriers": barriers_payload,
                "candidates": [],
                "selected_adaptation": None,
                "reason": NO_CANDIDATES_REASON,
            }

        candidates_sorted = sorted(pool.values(), key=lambda e: e["score_entry"].score, reverse=True)
        candidates_response = [
            {"adaptation_id": e["adaptation"].name, "score": e["score_entry"].score} for e in candidates_sorted
        ]

        selected_key, rationale, ai_used, ai_error = AdaptationRecommender._decide(
            candidates_sorted, pool, task, barriers_payload
        )

        # Safety validation: try the selected candidate, then degrade to the
        # next-best deterministic candidate if it's rejected (Phase 5
        # section 32: "Safety rejection: attempt the next safest
        # deterministic candidate").
        ordered = [pool[selected_key]] + [e for e in candidates_sorted if e["adaptation"].name != selected_key]
        approved_entry = None
        validation = None
        for entry in ordered:
            barrier_type = next(iter(entry["barrier_types"]))
            barrier = next(b for b in barriers if b.barrier_type == barrier_type)
            validation = AdaptationSafetyValidator.validate(entry["adaptation"], barrier, ability_profile, task)
            if validation.approved:
                approved_entry = entry
                break
            logger.info("Safety validation rejected '%s': %s", entry["adaptation"].name, validation.reason)

        if approved_entry is None:
            return {
                "barriers": barriers_payload,
                "candidates": candidates_response,
                "selected_adaptation": None,
                "reason": NO_SAFE_ADAPTATION,
            }

        source = "ai" if ai_used and approved_entry["adaptation"].name == selected_key else "deterministic_fallback"
        if source == "deterministic_fallback" and approved_entry["adaptation"].name != selected_key:
            rationale = (
                f"Deterministic fallback: '{approved_entry['adaptation'].display_name}' was the next-safest "
                f"candidate after the original selection failed safety validation ({validation.reason})."
            )

        return {
            "barriers": barriers_payload,
            "candidates": candidates_response,
            "selected_adaptation": {
                "adaptation_id": approved_entry["adaptation"].name,
                "name": approved_entry["adaptation"].display_name,
                "score": approved_entry["score_entry"].score,
                "barrier_types": sorted(approved_entry["barrier_types"]),
                "reason": rationale,
                "source": source,
                "validated": True,
                "requires_confirmation": validation.requires_confirmation,
                "ai_error": ai_error,
            },
        }

    @staticmethod
    def _decide(candidates_sorted, pool, task, barriers_payload) -> tuple[str, str, bool, str | None]:
        """Returns (selected_adaptation_id, rationale, ai_used, ai_error)."""

        top = candidates_sorted[0]
        fallback_key = top["adaptation"].name
        fallback_rationale = (
            f"Deterministic fallback: '{top['adaptation'].display_name}' scored highest "
            f"({top['score_entry'].score:.2f}) using Accessibility Benefit + Task Relevance + "
            f"User Preference + Confidence − Interaction Cost − Risk."
        )

        if not llm_client.is_configured():
            return fallback_key, fallback_rationale, False, None

        candidates_payload = [
            {
                "adaptation_id": e["adaptation"].name,
                "display_name": e["adaptation"].display_name,
                "resolves_barrier_types": sorted(e["barrier_types"]),
                "deterministic_score": e["score_entry"].score,
                "accessibility_benefit": round(e["score_entry"].accessibility_benefit, 3),
                "interaction_cost": round(e["score_entry"].interaction_cost, 3),
                "risk": round(e["score_entry"].risk, 3),
            }
            for e in candidates_sorted
        ]

        try:
            raw = llm_client.call(
                RECOMMENDER_SYSTEM_PROMPT, build_recommender_prompt(task, barriers_payload, candidates_payload)
            )
            parsed = AdaptationRecommendationResponse.model_validate(json.loads(raw))
        except (llm_client.LLMUnavailableError, json.JSONDecodeError, ValidationError) as exc:
            logger.warning("AI recommendation unavailable/invalid, using deterministic fallback: %s", exc)
            return fallback_key, fallback_rationale, False, str(exc)

        candidate_ids = set(pool.keys())
        if parsed.selected_adaptation_id not in candidate_ids:
            logger.warning(
                "AI selected unknown adaptation '%s' outside the candidate pool — falling back.",
                parsed.selected_adaptation_id,
            )
            return fallback_key, fallback_rationale, False, "AI selected an adaptation outside the candidate pool."

        if any(r.adaptation_id not in candidate_ids for r in parsed.ranked_adaptations):
            logger.warning("AI ranking referenced an adaptation outside the candidate pool — falling back.")
            return fallback_key, fallback_rationale, False, "AI ranking referenced an unknown adaptation."

        return parsed.selected_adaptation_id, parsed.overall_rationale, True, None
