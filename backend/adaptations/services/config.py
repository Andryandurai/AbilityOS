"""Centralized Adaptation Engine configuration (Phase 5).

Weights for the scoring formula:

    Score = (benefit * BENEFIT_WEIGHT) + (relevance * RELEVANCE_WEIGHT)
          + (preference * PREFERENCE_WEIGHT) + (confidence * CONFIDENCE_WEIGHT)
          - (cost * COST_WEIGHT) - (risk * RISK_WEIGHT)

All six weights are 1.0 — a deliberate choice, not an oversight. The
"smallest useful intervention" behaviour (Phase 5 section 12) comes from
the cost/risk *terms themselves* being genuinely larger for a more
disruptive adaptation, not from artificially weighting cost/risk higher
than benefit. Weighting one factor over another would let a hand-picked
multiplier silently override what the catalogue's own cost/risk values
say about an adaptation — the catalogue should speak for itself.

The final score is the existing project's raw sum (roughly -1.5 to 3.0 in
practice, not rescaled to a 0-5 or 0-100 range) — kept exactly as the
already-approved, already-tested `adaptations.services.scoring` module
computes it, rather than introducing a rescaling that would change
existing, tested behaviour for no functional benefit.
"""

from __future__ import annotations

ACCESSIBILITY_BENEFIT_WEIGHT = 1.0
TASK_RELEVANCE_WEIGHT = 1.0
USER_PREFERENCE_WEIGHT = 1.0
CONFIDENCE_WEIGHT = 1.0
INTERACTION_COST_WEIGHT = 1.0
RISK_WEIGHT = 1.0

# Rule 6/7 (Phase 5 section 25): an approved adaptation may only change
# *presentation* — never task/business data. Every `ui_effects` key an
# adaptation is allowed to carry is listed here; anything outside this set
# is rejected by AdaptationSafetyValidator as "introduces unsupported
# behaviour" rather than silently accepted.
ALLOWED_UI_EFFECT_KEYS = {
    "button_scale",
    "spacing_scale",
    "contrast",
    "text_scale",
    "flow",
    "choice_limit",
    "progress_indicator",
    "voice_prompts",
    "tts",
    "banner_alert",
    "haptics",
    "voice_input",
    "confirm_step",
}
