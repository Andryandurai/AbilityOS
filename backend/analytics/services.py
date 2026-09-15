"""AnalyticsService — every Phase 7 outcome calculation lives here, once.

Views (analytics/views.py) and the orchestrator (api/services/orchestrator.py)
both call into this module rather than each computing their own version of
"completion rate" or "learning signal" — Phase 7 section 35: "Do not
duplicate calculations across views/components."

Nothing here requires an AI provider. Every function is a deterministic
aggregation over already-persisted rows (Phase 7 section 34) and works
identically whether or not `AI_API_KEY` is configured.
"""

from __future__ import annotations

from django.db.models import Avg, Count, QuerySet

from adaptations.models import AdaptationResult
from analytics import config
from barriers.models import Barrier
from feedback.models import Feedback, InteractionEvent, InteractionSession

NOTE = (
    "Prototype demonstration metrics — computed from recorded InteractionSession/"
    "InteractionEvent/Feedback rows (seed data + live demo sessions), not a "
    "production research result."
)


# ---------------------------------------------------------------------------
# Per-session interaction counts, derived from InteractionEvent — the single
# source of truth for retries/backtracks/errors/assistance, so these numbers
# are never duplicated as separately-maintained counters elsewhere.
# ---------------------------------------------------------------------------
def session_interaction_counts(session: InteractionSession) -> dict:
    events = session.events.all()
    return {
        "errors_count": events.filter(event_type__in=InteractionEvent.ERROR_EVENT_TYPES).count(),
        "retries_count": events.filter(event_type__in=InteractionEvent.RETRY_EVENT_TYPES).count(),
        "backtracks_count": events.filter(event_type__in=InteractionEvent.BACKTRACK_EVENT_TYPES).count(),
        "assistance_count": events.filter(event_type=InteractionEvent.ASSISTANCE_REQUESTED).count(),
    }


# ---------------------------------------------------------------------------
# Outcome Score (Phase 7 section 18/19) — see analytics/config.py for the
# documented, centralized weights this reads.
# ---------------------------------------------------------------------------
def calculate_outcome_score(session: InteractionSession, feedback: Feedback | None) -> dict:
    w = config.OUTCOME_SCORE_WEIGHTS
    completed = bool(feedback and feedback.completed)

    completion_component = 1.0 if completed else 0.0

    assistance_requests = min(session.assistance_count, config.ASSISTANCE_REDUCTION_MAX_REQUESTS)
    assistance_component = max(0.0, 1.0 - assistance_requests * config.ASSISTANCE_REDUCTION_STEP)

    errors = feedback.errors if feedback else 0
    error_component = max(0.0, 1.0 - min(errors, config.ERROR_NORMALIZATION_CAP) / config.ERROR_NORMALIZATION_CAP)

    if feedback and feedback.ease_rating:
        ease_component = (feedback.ease_rating - 1) / 4  # 1..5 -> 0..1
    else:
        ease_component = 0.5  # no rating given -> neutral, never assumed positive or negative

    time_penalty = 0.0
    limit = getattr(session.task, "time_limit_seconds", None)
    if limit and session.completion_time_ms is not None:
        overrun = max(0.0, (session.completion_time_ms / 1000 - limit) / limit)
        time_penalty = min(1.0, overrun / config.TIME_OVERRUN_FOR_MAX_PENALTY)

    raw = (
        completion_component * w["completion"]
        + assistance_component * w["assistance_reduction"]
        + error_component * w["error_reduction"]
        + ease_component * w["ease_improvement"]
        - time_penalty * w["time_penalty"]
    )
    score = round(max(0.0, min(1.0, raw)), 3)

    return {
        "score": score,
        "components": {
            "completion": completion_component,
            "assistance_reduction": assistance_component,
            "error_reduction": error_component,
            "ease_improvement": ease_component,
            "time_penalty": time_penalty,
        },
    }


# ---------------------------------------------------------------------------
# Learning Signal (Phase 7 section 20/50) — structured evidence about ONE
# session, deterministic, never persisted as a second copy of the truth
# (it's fully derivable from Feedback + AdaptationResult + Barrier rows
# already stored, so it's computed on demand here instead of stored again).
# ---------------------------------------------------------------------------
def generate_learning_signal(session: InteractionSession, feedback: Feedback | None) -> dict | None:
    applied_result = (
        session.adaptation_results.select_related("adaptation", "barrier").filter(applied=True).first()
    )
    if feedback is None or applied_result is None:
        return None

    completed = feedback.completed
    no_assistance = session.assistance_count == 0 and not feedback.assistance_requested
    ease_ok = feedback.ease_rating is None or feedback.ease_rating >= config.INDEPENDENCE_EASE_FLOOR

    successful = bool(completed)
    independence_improved = bool(completed and no_assistance and ease_ok)

    return {
        "adaptation_id": applied_result.adaptation.name,
        "task_id": session.task.task_id,
        "barrier_type": applied_result.barrier.barrier_type,
        "successful": successful,
        "independence_improved": independence_improved,
        "confidence": config.SINGLE_SESSION_CONFIDENCE,
    }


# ---------------------------------------------------------------------------
# Aggregate bucket metrics (extends the pre-existing before/after helper
# with average ease, now that Feedback carries it) — used by both
# analytics/before-after and the new adaptation/barrier breakdowns.
# ---------------------------------------------------------------------------
def bucket_metrics(feedback_qs: QuerySet[Feedback]) -> dict:
    total = feedback_qs.count()
    if total == 0:
        return {
            "sessions": 0,
            "completion_rate": None,
            "avg_time_seconds": None,
            "avg_errors": None,
            "assistance_rate": None,
            "avg_ease": None,
        }
    completed = feedback_qs.filter(completed=True).count()
    assisted = feedback_qs.filter(assistance_requested=True).count()
    aggregates = feedback_qs.aggregate(
        avg_time=Avg("time_seconds"), avg_errors=Avg("errors"), avg_ease=Avg("ease_rating")
    )
    return {
        "sessions": total,
        "completion_rate": round(completed / total, 3),
        "avg_time_seconds": round(aggregates["avg_time"] or 0, 1),
        "avg_errors": round(aggregates["avg_errors"] or 0, 2),
        "assistance_rate": round(assisted / total, 3),
        "avg_ease": round(aggregates["avg_ease"], 2) if aggregates["avg_ease"] is not None else None,
    }


def _effectiveness_state(completion_rate, assistance_rate, avg_ease, sessions) -> str:
    if sessions < config.MIN_SESSIONS_FOR_SIGNAL:
        return config.INSUFFICIENT_DATA

    if completion_rate < config.NEGATIVE_COMPLETION_RATE_CEILING or (
        avg_ease is not None and avg_ease < config.NEGATIVE_AVG_EASE_CEILING
    ):
        return config.NEGATIVE_OBSERVED_OUTCOME

    ease_ok = avg_ease is None or avg_ease >= config.POSITIVE_AVG_EASE_FLOOR
    if (
        completion_rate >= config.POSITIVE_COMPLETION_RATE_FLOOR
        and assistance_rate <= config.POSITIVE_ASSISTANCE_RATE_CEILING
        and ease_ok
    ):
        return config.POSITIVE_OBSERVED_OUTCOME

    return config.INCONCLUSIVE


def _aggregate_confidence(sessions: int) -> float:
    return round(
        min(config.AGGREGATE_CONFIDENCE_CAP, config.AGGREGATE_CONFIDENCE_BASE + sessions * config.AGGREGATE_CONFIDENCE_PER_SESSION),
        2,
    )


def adaptation_effectiveness() -> list[dict]:
    """Phase 7 section 17/51: per-adaptation outcome evidence, applied
    sessions only (an adaptation that was merely *approved* but never
    actually applied to an interface tells us nothing about its outcome)."""

    # .order_by() clears AdaptationResult's default Meta ordering (`-score`)
    # before .distinct() — without it, DISTINCT operates on the *hidden*
    # (score, adaptation_id) tuple Django adds for the ordering, not just
    # adaptation_id, so the same adaptation applied across sessions with
    # different scores silently produced duplicate rows here (caught via a
    # live Playwright run showing a duplicate-React-key console error).
    applied_adaptation_ids = (
        AdaptationResult.objects.filter(applied=True)
        .order_by()
        .values_list("adaptation_id", flat=True)
        .distinct()
    )
    results = []
    for adaptation_id in applied_adaptation_ids:
        applied_results = AdaptationResult.objects.filter(adaptation_id=adaptation_id, applied=True)
        adaptation = applied_results.first().adaptation
        session_ids = applied_results.order_by().values_list("session_id", flat=True).distinct()
        feedback_qs = Feedback.objects.filter(session_id__in=session_ids)
        metrics = bucket_metrics(feedback_qs)

        assistance_rate = metrics["assistance_rate"] if metrics["assistance_rate"] is not None else 0.0
        completion_rate = metrics["completion_rate"] if metrics["completion_rate"] is not None else 0.0
        state = _effectiveness_state(completion_rate, assistance_rate, metrics["avg_ease"], metrics["sessions"])

        results.append(
            {
                "adaptation_id": adaptation.name,
                "display_name": adaptation.display_name,
                "sessions": metrics["sessions"],
                "completion_rate": metrics["completion_rate"],
                "avg_ease": metrics["avg_ease"],
                "assistance_rate": metrics["assistance_rate"],
                "avg_errors": metrics["avg_errors"],
                "observed_outcome": state,
                "confidence": _aggregate_confidence(metrics["sessions"]) if state != config.INSUFFICIENT_DATA else None,
            }
        )
    return sorted(results, key=lambda r: r["sessions"], reverse=True)


def barrier_outcomes() -> list[dict]:
    """Phase 7 section 23: per-barrier frequency, associated adaptations,
    and outcome success — the barrier side of the same evidence
    `adaptation_effectiveness()` reports from the adaptation side."""

    # See the matching comment in adaptation_effectiveness() — .order_by()
    # defensively clears Barrier's default `-severity` ordering before
    # .distinct() for the same reason, even though today's seeded data
    # doesn't happen to trigger a visible duplicate here.
    barrier_types = Barrier.objects.order_by().values_list("barrier_type", flat=True).distinct()
    results = []
    for barrier_type in barrier_types:
        frequency = Barrier.objects.filter(barrier_type=barrier_type).count()

        associated = (
            AdaptationResult.objects.filter(barrier__barrier_type=barrier_type, applied=True)
            .values("adaptation__name", "adaptation__display_name")
            .annotate(times_used=Count("id"))
            .order_by("-times_used")
        )

        session_ids = (
            AdaptationResult.objects.filter(barrier__barrier_type=barrier_type, applied=True)
            .order_by()
            .values_list("session_id", flat=True)
            .distinct()
        )
        feedback_qs = Feedback.objects.filter(session_id__in=session_ids)
        metrics = bucket_metrics(feedback_qs)
        completion_rate = metrics["completion_rate"] if metrics["completion_rate"] is not None else 0.0
        assistance_rate = metrics["assistance_rate"] if metrics["assistance_rate"] is not None else 0.0
        state = _effectiveness_state(completion_rate, assistance_rate, metrics["avg_ease"], metrics["sessions"])

        results.append(
            {
                "barrier_type": barrier_type,
                "frequency": frequency,
                "associated_adaptations": list(associated),
                "outcome_sessions": metrics["sessions"],
                "observed_outcome": state,
            }
        )
    return sorted(results, key=lambda r: r["frequency"], reverse=True)
