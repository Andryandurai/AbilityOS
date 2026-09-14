"""Aggregate metrics (Part 6 Module 12, Part 18, Part 22).

Every number here is computed from real InteractionSession/Feedback rows —
seeded demo rows are included but explicitly labelled, never presented as
production research findings (Part 18's caution against faking metrics).
"""

from __future__ import annotations

from django.db.models import Avg, Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from adaptations.models import AdaptationResult
from feedback.models import Feedback, InteractionSession

NOTE = (
    "Prototype demonstration metrics — computed from recorded InteractionSession/"
    "Feedback rows (seed data + live demo sessions), not a production research result."
)


def _bucket_metrics(feedback_qs):
    total = feedback_qs.count()
    if total == 0:
        return {
            "sessions": 0,
            "completion_rate": None,
            "avg_time_seconds": None,
            "avg_errors": None,
            "assistance_rate": None,
        }
    completed = feedback_qs.filter(completed=True).count()
    assisted = feedback_qs.filter(assistance_requested=True).count()
    aggregates = feedback_qs.aggregate(avg_time=Avg("time_seconds"), avg_errors=Avg("errors"))
    return {
        "sessions": total,
        "completion_rate": round(completed / total, 3),
        "avg_time_seconds": round(aggregates["avg_time"] or 0, 1),
        "avg_errors": round(aggregates["avg_errors"] or 0, 2),
        "assistance_rate": round(assisted / total, 3),
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def before_after(request):
    """GET /api/analytics/before-after/."""

    without_qs = Feedback.objects.filter(session__baseline_mode=True)
    with_qs = Feedback.objects.filter(session__baseline_mode=False)

    return Response(
        {
            "note": NOTE,
            "without_abilityos": _bucket_metrics(without_qs),
            "with_abilityos": _bucket_metrics(with_qs),
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard(request):
    """GET /api/analytics/dashboard/ (Part 22 analytics dashboard)."""

    sessions = InteractionSession.objects.all()
    feedback_qs = Feedback.objects.all()

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
            "note": NOTE,
            "total_interactions": sessions.count(),
            "completed_tasks": sessions.filter(status=InteractionSession.STATUS_COMPLETED).count(),
            "overall": _bucket_metrics(feedback_qs),
            "adaptations_used": list(adaptation_usage),
            "profile_distribution": list(profile_distribution),
        }
    )
