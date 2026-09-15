"""Centralized, documented constants for every Phase 7 outcome calculation.

Every number an analytics view or the learning signal reports traces back
to a named constant here — never an inline magic number in a view or
service function (Phase 7 section 35/50: "the exact thresholds should be
documented and centralized"). Nothing in this module calls an LLM or any
external service; every calculation it backs is a deterministic function
of `InteractionSession`/`InteractionEvent`/`Feedback`/`AdaptationResult`
rows already in the database (Phase 7 section 34).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Outcome Score (Phase 7 section 18) — a single, transparent 0.0-1.0 number
# combining objective and subjective evidence for one session. It is never
# used to gate anything automatically (see LEARNING SIGNAL below); it exists
# purely so "how did this session go" has one comparable number across the
# analytics views.
#
# Phase 7 section 19 is explicit that completion time is the *least*
# important signal — successful, independent completion matters far more
# than speed. These weights encode that ordering directly: completion and
# independence-from-assistance dominate; a time penalty only ever
# subtracts, and only when the task itself defines a time budget.
# ---------------------------------------------------------------------------
OUTCOME_SCORE_WEIGHTS = {
    "completion": 0.35,
    "assistance_reduction": 0.20,
    "error_reduction": 0.20,
    "ease_improvement": 0.20,
    "time_penalty": 0.05,  # subtracted, not added
}

# An error/retry count at or above this is treated as "as bad as it gets"
# for the error-reduction component (further errors don't reduce the score
# further — there is no benefit to over-penalizing a already-poor session).
ERROR_NORMALIZATION_CAP = 5

# assistance_count -> reduction credit. 0 requests is full credit; every
# additional request costs the same amount, floaring at 0 (Phase 7 section
# 11: the system must distinguish 0 / 1 / 2+, not just a boolean).
ASSISTANCE_REDUCTION_STEP = 0.5
ASSISTANCE_REDUCTION_MAX_REQUESTS = 2

# How far over a task's own `time_limit_seconds` counts as the worst-case
# time penalty (100% of the penalty weight). Only applied when the task
# defines a limit at all — never a default guess about how fast "should"
# be, per section 19.
TIME_OVERRUN_FOR_MAX_PENALTY = 1.0  # i.e. taking 2x the limit -> full penalty

# ---------------------------------------------------------------------------
# Learning Signal (Phase 7 section 20/50) — structured evidence, not a
# statistical claim. `confidence` here is deliberately small for a single
# session; see ADAPTATION_EFFECTIVENESS below for how confidence grows with
# more evidence.
# ---------------------------------------------------------------------------
SINGLE_SESSION_CONFIDENCE = 0.3

# A session only counts as "independence improved" when it was completed
# with no assistance and (if rated) a comfortable ease rating.
INDEPENDENCE_EASE_FLOOR = 4  # Feedback.EASE_EASY

# ---------------------------------------------------------------------------
# Adaptation / barrier effectiveness aggregation (Phase 7 section 17/51) —
# states are deliberately coarse and always shown with their evidence
# (session count, completion rate, avg ease) rather than as a bare label.
# ---------------------------------------------------------------------------
INSUFFICIENT_DATA = "insufficient_data"
POSITIVE_OBSERVED_OUTCOME = "positive_observed_outcome"
NEGATIVE_OBSERVED_OUTCOME = "negative_observed_outcome"
INCONCLUSIVE = "inconclusive"

MIN_SESSIONS_FOR_SIGNAL = 3

POSITIVE_COMPLETION_RATE_FLOOR = 0.7
POSITIVE_ASSISTANCE_RATE_CEILING = 0.3
POSITIVE_AVG_EASE_FLOOR = 3.5

NEGATIVE_COMPLETION_RATE_CEILING = 0.5
NEGATIVE_AVG_EASE_CEILING = 2.5

# Aggregate confidence grows with sample size but is capped — this project
# never claims statistical certainty (Phase 7 section 37/50).
AGGREGATE_CONFIDENCE_BASE = 0.3
AGGREGATE_CONFIDENCE_PER_SESSION = 0.08
AGGREGATE_CONFIDENCE_CAP = 0.9
