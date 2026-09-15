"""Prompt construction for the AI Decision Engine (Part 7).

The guiding principle for the whole project: "AI may reason about the
adaptation, but it must not invent the user's ability profile." This module
enforces that at the data layer — the prompt is built only from the
confirmed AbilityProfile dimensions relevant to the detected barriers, the
TaskDescriptor, the barriers themselves, and the pre-scored candidate
adaptations. No free-text personal information, and no adaptation outside
the supplied candidate list, is ever included.
"""

from __future__ import annotations

import json

SYSTEM_PROMPT = (
    "You are the AI Decision Engine inside AbilityOS, an accessibility reasoning layer. "
    "For each detected barrier you are given a fixed list of candidate adaptations with "
    "pre-computed scores. Your job is to pick, for EACH barrier, exactly one "
    "selected_adaptation from that barrier's candidate list — never invent a new "
    "adaptation name, and never invent facts about the person beyond what is given. "
    "Prefer the smallest adaptation that plausibly resolves the barrier; only prefer a "
    "higher-cost candidate over the top-scored one if you have a clear, stated reason. "
    "Respond ONLY with JSON matching this shape: "
    '{"decisions": [{"barrier_type": "...", "selected_adaptation": "...", '
    '"confidence": 0.0-1.0, "rationale": "one short sentence"}]}'
)


def build_user_prompt(task_descriptor: dict, barriers_payload: list[dict]) -> str:
    payload = {
        "task": task_descriptor,
        "barriers": barriers_payload,
    }
    return (
        "Decide the smallest useful adaptation for each barrier below. "
        "Only use adaptation ids present in that barrier's `candidates` list.\n\n"
        + json.dumps(payload, indent=2)
    )


# --- Phase 5: single-recommendation contract (adaptations/services/recommender.py) ---
RECOMMENDER_SYSTEM_PROMPT = (
    "You are the AbilityOS Adaptation Decision Engine. You are given the barriers "
    "already detected for one person doing one task, and a fixed pool of candidate "
    "adaptations (each pre-scored deterministically) that could address them. "
    "You may ONLY choose from the provided candidate adaptation ids — never invent a "
    "new adaptation, and never invent facts about the person, task, environment, or "
    "barriers beyond what is given. Rank the full candidate pool and name exactly one "
    "overall selected_adaptation_id: the smallest intervention that plausibly resolves "
    "the barrier(s), not necessarily the most powerful one. Respond ONLY with JSON "
    "matching this shape: "
    '{"selected_adaptation_id": "...", '
    '"ranked_adaptations": [{"adaptation_id": "...", "rank": 1, "rationale": "..."}], '
    '"overall_rationale": "one to two short sentences"}'
)


def build_recommender_prompt(task_descriptor: dict, barriers_payload: list[dict], candidates_payload: list[dict]) -> str:
    payload = {
        "task": task_descriptor,
        "detected_barriers": barriers_payload,
        "candidate_adaptations": candidates_payload,
    }
    return (
        "Rank the candidate adaptations below and select exactly one overall "
        "selected_adaptation_id. Only use adaptation_id values present in "
        "`candidate_adaptations`.\n\n" + json.dumps(payload, indent=2)
    )
