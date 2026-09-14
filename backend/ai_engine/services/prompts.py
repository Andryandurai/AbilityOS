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
