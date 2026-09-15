"""Aggregate metrics (Part 6 Module 12, Part 18, Part 22; extended Phase 7).

Every number here is computed from real InteractionSession/InteractionEvent/
Feedback rows — seeded demo rows are included but explicitly labelled, never
presented as production research findings (Part 18's caution against faking
metrics). All calculations live in analytics/services.py (Phase 7 section 35:
"Do not duplicate calculations across views/components") — this module only
shapes HTTP responses.
"""

from __future__ import annotations

from django.db.models import Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from adaptations.models import AdaptationResult
from analytics import services
from feedback.models import Feedback, InteractionSession


@api_view(["GET"])
@permission_classes([AllowAny])
def before_after(request):
    """GET /api/analytics/before-after/ — standard (baseline_mode=True) vs.
    adaptive (baseline_mode=False) experience for the same task, Phase 7
    section 15/37's "Standard vs Adaptive" comparison."""

    without_qs = Feedback.objects.filter(session__baseline_mode=True)
    with_qs = Feedback.objects.filter(session__baseline_mode=False)

    return Response(
        {
            "note": services.NOTE,
            "without_abilityos": services.bucket_metrics(without_qs),
            "with_abilityos": services.bucket_metrics(with_qs),
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard(request):
    """GET /api/analytics/dashboard/ (Part 22 analytics dashboard)."""

    sessions = InteractionSession.objects.all()
    feedback_qs = Feedback.objects.all()

    if sessions.count() == 0:
        return Response({"note": services.NOTE, "empty": True})

    adaptation_usage = (
        AdaptationResult.objects.filter(applied=True)
        .values("adaptation__name", "adaptation__display_name")
        .annotate(times_used=Count("id"))
        .order_by("-times_used")
    )

    profile_distribution = (
        sessions.values("user__ability_profile__label").annotate(count=Count("id")).order_by("-count")
    )

    return Response(
        {
            "note": services.NOTE,
            "empty": False,
            "total_interactions": sessions.count(),
            "completed_tasks": sessions.filter(status=InteractionSession.STATUS_COMPLETED).count(),
            "abandoned_tasks": sessions.filter(status=InteractionSession.STATUS_ABANDONED).count(),
            "overall": services.bucket_metrics(feedback_qs),
            "adaptations_used": list(adaptation_usage),
            "profile_distribution": list(profile_distribution),
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def adaptations(request):
    """GET /api/analytics/adaptations/ — Phase 7 section 17/51: per-
    adaptation outcome evidence with a transparent, documented
    observed-outcome state (never a bare "AI says this works")."""

    results = services.adaptation_effectiveness()
    return Response({"note": services.NOTE, "empty": len(results) == 0, "adaptations": results})


@api_view(["GET"])
@permission_classes([AllowAny])
def barriers(request):
    """GET /api/analytics/barriers/ — Phase 7 section 23: per-barrier
    frequency, associated adaptations, and outcome success."""

    results = services.barrier_outcomes()
    return Response({"note": services.NOTE, "empty": len(results) == 0, "barriers": results})


@api_view(["GET"])
@permission_classes([AllowAny])
def sessions(request):
    """GET /api/analytics/sessions/?limit=10 — Phase 7 section 40's "Recent
    Sessions" table. `is_seed` is always included so demo-seeded rows are
    never presented indistinguishably from a live session (section 38)."""

    try:
        limit = min(50, max(1, int(request.query_params.get("limit", 10))))
    except ValueError:
        limit = 10

    recent = (
        InteractionSession.objects.select_related("task", "feedback")
        .order_by("-created_at")[:limit]
    )
    results = [
        {
            "session_id": s.pk,
            "task_name": s.task.name,
            "experience_mode": s.experience_mode,
            "status": s.status,
            "ease_rating": getattr(s.feedback, "ease_rating", None) if hasattr(s, "feedback") else None,
            "assistance_requested": getattr(s.feedback, "assistance_requested", None) if hasattr(s, "feedback") else None,
            "is_seed": s.is_seed,
            "created_at": s.created_at,
        }
        for s in recent
    ]
    return Response({"note": services.NOTE, "empty": len(results) == 0, "sessions": results})
