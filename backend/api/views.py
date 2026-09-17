"""Orchestrator-backed endpoints — one per stage of the Part 5 workflow.

Views stay thin: validate input, delegate to InteractionOrchestrator, shape
the response. All the actual reasoning lives in the app-level services.
"""

from __future__ import annotations

import django
from django.conf import settings
from django.db import connection
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from abilities.services.profile_service import get_or_create_profile
from adaptations.serializers import AdaptationResultSerializer
from adaptations.services.recommender import AdaptationRecommender
from api.services.orchestrator import DEFAULT_ENVIRONMENT_ID, InteractionOrchestrator, OrchestratorError
from api.services.what_if import WhatIfValidationError
from api.services.what_if import simulate as run_what_if_simulation
from barriers.serializers import BarrierSerializer
from barriers.services.detector import BarrierDetectionService
from environments.serializers import EnvironmentSerializer
from environments.services.analyzer import EnvironmentAnalyzer, EnvironmentNotFoundError
from feedback.models import InteractionSession
from feedback.serializers import FeedbackSerializer, InteractionEventSerializer
from tasks.services.task_service import TaskNotFoundError, get_task_descriptor
from users.models import User
from users.services.consent_service import is_consented_for_adaptation
from users.services.ownership import assert_owner


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """GET /api/health/ — Phase 1 foundation check.

    Proves the full React -> Django -> Database chain actually works, not
    just that the process is alive: it runs a real query against whichever
    database is configured (PostgreSQL via DATABASE_URL, or the SQLite
    development fallback) and reports what it found.
    """

    db_engine = connection.settings_dict.get("ENGINE", "")
    db_ok = True
    db_error = None
    user_count = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        user_count = User.objects.count()
    except Exception as exc:  # pragma: no cover - defensive, exercised only if DB is down
        db_ok = False
        db_error = str(exc)

    return Response(
        {
            "status": "ok" if db_ok else "degraded",
            "service": "AbilityOS API",
            "django_version": django.get_version(),
            "database": {
                "engine": "postgresql" if "postgresql" in db_engine else "sqlite",
                "connected": db_ok,
                "error": db_error,
                "seeded_user_count": user_count,
            },
            "ai_decision_engine": {
                "provider": settings.AI_PROVIDER,
                "configured": settings.AI_AVAILABLE,
            },
        },
        status=status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


class StartInteractionView(APIView):
    """POST /api/interactions/start/ — {"user_id", "task_id", "environment_id"?, "baseline_mode"?}."""

    permission_classes = [AllowAny]
    throttle_scope = "session_start"

    def post(self, request):
        user = get_object_or_404(User, pk=request.data.get("user_id"))
        assert_owner(request, user.id, "You may only start a session for your own profile.")
        task_id = request.data.get("task_id")
        if not task_id:
            return Response({"detail": "task_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        session = InteractionOrchestrator.start(
            user=user,
            task_id=task_id,
            environment_id=request.data.get("environment_id"),
            baseline_mode=bool(request.data.get("baseline_mode", False)),
        )
        return Response({"session_id": session.pk, "status": session.status}, status=status.HTTP_201_CREATED)


class AnalyzeEnvironmentView(APIView):
    """POST /api/environment/analyze/

    Two calling conventions on the same endpoint:
    - {"session_id", "image_base64"?} — the existing orchestrator-driven
      flow (Part 5/14), attaches the analyzed environment to a live
      InteractionSession.
    - {"environment_id"} with no session_id — the Phase 3 Task/Environment
      Understanding demo: a standalone, deterministic fixture lookup that
      returns an EnvironmentDescriptor with no session involved. This is
      the Environment Understanding Engine's actual entry point; the
      session-based form above is what the orchestrator uses internally.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        session_id = request.data.get("session_id")
        environment_id = request.data.get("environment_id")

        if not session_id:
            if not environment_id:
                return Response(
                    {"detail": "Provide either session_id or environment_id."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                descriptor = EnvironmentAnalyzer.analyze_fixture(environment_id)
            except EnvironmentNotFoundError as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
            return Response(descriptor)

        session = get_object_or_404(InteractionSession, pk=session_id)
        assert_owner(request, session.user_id, "You may only access your own session.")
        environment = InteractionOrchestrator.analyze_environment(
            session, image_base64=request.data.get("image_base64")
        )
        if environment is None:
            return Response(
                {"detail": "No environment fixture available for this task."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(EnvironmentSerializer(environment).data)


class DetectBarriersView(APIView):
    """POST /api/barriers/detect/

    Two calling conventions on the same endpoint (same pattern as
    AnalyzeEnvironmentView — Phase 3):
    - {"session_id"} — the existing orchestrator-driven flow, persists
      Barrier rows against a live InteractionSession.
    - {"user_id", "task_id", "environment_id"} — the Phase 4 Barrier
      Detection Engine demo: a standalone, deterministic, non-persisting
      call. Reuses the exact Phase 2/3 services (profile_service,
      task_service, EnvironmentAnalyzer) rather than re-fetching or
      re-deriving any of that data itself.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        session_id = request.data.get("session_id")
        if session_id:
            session = get_object_or_404(InteractionSession, pk=session_id)
            assert_owner(request, session.user_id, "You may only access your own session.")
            barriers = InteractionOrchestrator.detect_barriers(session)
            return Response({"barriers": BarrierSerializer(barriers, many=True).data})

        return self._detect_standalone(request)

    def _detect_standalone(self, request):
        user_id = request.data.get("user_id")
        task_id = request.data.get("task_id")
        environment_id = request.data.get("environment_id")

        if not (user_id and task_id and environment_id):
            return Response(
                {"detail": "Provide session_id, or all of user_id/task_id/environment_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = get_object_or_404(User, pk=user_id)
        assert_owner(request, user.id, "You may only run barrier detection for your own profile.")

        if not is_consented_for_adaptation(user):
            raise PermissionDenied(
                "Consent required before AbilityOS can use this profile for barrier detection."
            )

        try:
            task_descriptor = get_task_descriptor(task_id)
        except TaskNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        try:
            environment_descriptor = EnvironmentAnalyzer.analyze_fixture(environment_id)
        except EnvironmentNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        profile = get_or_create_profile(user)
        results = BarrierDetectionService.detect(profile.dimensions, task_descriptor, environment_descriptor)

        return Response(
            {
                "user_id": user.id,
                "task_id": task_id,
                "environment_id": environment_id,
                "barriers": [r.as_dict() for r in results],
            }
        )


class RecommendAdaptationsView(APIView):
    """POST /api/adaptations/recommend/

    Two calling conventions on the same endpoint (same dual-mode pattern as
    Phase 3/4's analyze endpoints):
    - {"session_id"} — the existing orchestrator-driven flow, persists
      AdaptationResult rows against a live InteractionSession.
    - {"user_id", "task_id", "environment_id"} — the Phase 5 Adaptation +
      AI Decision Engine demo: a standalone, non-persisting call that runs
      Phase 4 barrier detection then AdaptationRecommender on top of it.
    """

    permission_classes = [AllowAny]
    throttle_scope = "adaptation_recommend"

    def post(self, request):
        session_id = request.data.get("session_id")
        if session_id:
            session = get_object_or_404(InteractionSession, pk=session_id)
            assert_owner(request, session.user_id, "You may only access your own session.")
            results = InteractionOrchestrator.recommend_adaptations(session)
            return Response(
                {"ai_used": session.ai_used, "results": AdaptationResultSerializer(results, many=True).data}
            )

        return self._recommend_standalone(request)

    def _recommend_standalone(self, request):
        user_id = request.data.get("user_id")
        task_id = request.data.get("task_id")
        environment_id = request.data.get("environment_id")

        if not (user_id and task_id and environment_id):
            return Response(
                {"detail": "Provide session_id, or all of user_id/task_id/environment_id."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = get_object_or_404(User, pk=user_id)
        assert_owner(request, user.id, "You may only recommend adaptations for your own profile.")

        if not is_consented_for_adaptation(user):
            raise PermissionDenied(
                "Consent required before AbilityOS can recommend an adaptation for this profile."
            )

        try:
            task_descriptor = get_task_descriptor(task_id)
        except TaskNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        try:
            environment_descriptor = EnvironmentAnalyzer.analyze_fixture(environment_id)
        except EnvironmentNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        profile = get_or_create_profile(user)
        result = AdaptationRecommender.recommend(
            profile.dimensions, task_descriptor, environment_descriptor, profile.preferred_modality
        )

        return Response(result)


class ApplyAdaptationView(APIView):
    """POST /api/interactions/{id}/apply/ — {"confirmed_ids"?: [1, 2]}."""

    permission_classes = [AllowAny]

    def post(self, request, session_id):
        session = get_object_or_404(InteractionSession, pk=session_id)
        assert_owner(request, session.user_id, "You may only access your own session.")
        payload = InteractionOrchestrator.apply(session, confirmed_ids=request.data.get("confirmed_ids"))
        return Response(payload)


class RecordEventsView(APIView):
    """POST /api/interactions/{id}/events/ — Phase 7 step-level interaction
    tracking. Accepts either one event object or {"events": [...]}, so the
    frontend can batch a queue instead of one request per tap (section 29)."""

    permission_classes = [AllowAny]

    def post(self, request, session_id):
        session = get_object_or_404(InteractionSession, pk=session_id)
        assert_owner(request, session.user_id, "You may only access your own session.")
        payload = request.data.get("events") if "events" in request.data else [request.data]
        if not isinstance(payload, list) or not payload:
            return Response({"detail": "Provide an event object or a non-empty 'events' list."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            events = InteractionOrchestrator.record_events(session, payload)
        except OrchestratorError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        session.refresh_from_db()
        return Response(
            {
                "recorded": len(events),
                "events": InteractionEventSerializer(events, many=True).data,
                "status": session.status,
                "assistance_count": session.assistance_count,
            },
            status=status.HTTP_201_CREATED,
        )


class CompleteInteractionView(APIView):
    """POST /api/interactions/{id}/complete/ — Phase 7 explicit lifecycle
    (section 7/26): marks the session completed with a server-authoritative
    `completed_at`, ahead of the separate feedback step."""

    permission_classes = [AllowAny]

    def post(self, request, session_id):
        session = get_object_or_404(InteractionSession, pk=session_id)
        assert_owner(request, session.user_id, "You may only access your own session.")
        try:
            session = InteractionOrchestrator.complete(session)
        except OrchestratorError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(
            {"status": session.status, "completed_at": session.completed_at, "completion_time_ms": session.completion_time_ms}
        )


class AbandonInteractionView(APIView):
    """POST /api/interactions/{id}/abandon/ — {"reason"?: "..."}."""

    permission_classes = [AllowAny]

    def post(self, request, session_id):
        session = get_object_or_404(InteractionSession, pk=session_id)
        assert_owner(request, session.user_id, "You may only access your own session.")
        try:
            session = InteractionOrchestrator.abandon(session, reason=request.data.get("reason", ""))
        except OrchestratorError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response({"status": session.status, "completed_at": session.completed_at})


class InteractionFeedbackView(APIView):
    """POST /api/interactions/{id}/feedback/."""

    permission_classes = [AllowAny]

    def post(self, request, session_id):
        session = get_object_or_404(InteractionSession, pk=session_id)
        assert_owner(request, session.user_id, "You may only submit feedback for your own session.")
        try:
            feedback = InteractionOrchestrator.record_feedback(session, request.data)
        except OrchestratorError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"status": "recorded", "feedback": FeedbackSerializer(feedback).data}
        )


class InteractionSummaryView(APIView):
    """GET /api/interactions/{id}/summary/ — full developer-panel payload.

    Phase 6 (Feedback + History + Analytics) reuses this unmodified as the
    session-detail source for HistoryPage.jsx's "View Details" — it already
    returns everything a historical record needs (barriers, adaptation
    results, feedback, outcome score, learning signal, and the session's
    own `ability_profile_snapshot` — never a live re-read of the current
    AbilityProfile, see feedback/models.py's InteractionSession docstring),
    and was already ownership-enforced since Phase 1/8.
    """

    permission_classes = [AllowAny]

    def get(self, request, session_id):
        session = get_object_or_404(InteractionSession, pk=session_id)
        assert_owner(request, session.user_id, "You may only access your own session.")
        return Response(InteractionOrchestrator.summary(session))


class UserSessionsView(APIView):
    """GET /api/users/{id}/sessions/ (Phase 6) — the authenticated user's
    own interaction history, newest first, for HistoryPage.jsx's list.

    Deliberately a new, separately-owned endpoint rather than teaching the
    pre-existing GET /api/analytics/sessions/ to behave differently for an
    authenticated caller (see docs/HISTORY_ANALYTICS.md "Why a new
    endpoint"): that endpoint's entire purpose is AnalyticsPage.jsx's
    intentionally *global*, cross-user "Recent sessions" demo table (Phase
    7) — reused completely unmodified here, so that page's behaviour for
    every existing caller (anonymous or authenticated) is unchanged.
    """

    permission_classes = [IsAuthenticated]
    MAX_RESULTS = 50

    def get(self, request, user_id):
        assert_owner(request, user_id, "You may only view your own session history.")
        user = get_object_or_404(User, pk=user_id)

        session_qs = (
            InteractionSession.objects.filter(user=user)
            .select_related("task", "environment", "feedback")
            .prefetch_related("barriers", "adaptation_results")
            .order_by("-created_at")[: self.MAX_RESULTS]
        )

        results = []
        for session in session_qs:
            has_feedback = hasattr(session, "feedback")
            applied_count = sum(1 for r in session.adaptation_results.all() if r.applied)
            results.append(
                {
                    "session_id": session.pk,
                    "task_name": session.task.name,
                    "environment_name": session.environment.name if session.environment else None,
                    "status": session.status,
                    "experience_mode": session.experience_mode,
                    "barriers_detected": len(session.barriers.all()),
                    "adaptations_applied": applied_count,
                    "feedback_submitted": has_feedback,
                    "ease_rating": session.feedback.ease_rating if has_feedback else None,
                    "completed_flag": session.feedback.completed if has_feedback else None,
                    "created_at": session.created_at,
                    "completed_at": session.completed_at,
                    "is_seed": session.is_seed,
                }
            )
        return Response({"sessions": results})


class WhatIfSimulateView(APIView):
    """POST /api/what-if/simulate/ (Phase 7 — Advanced Adaptive Intelligence).

    {"task_id": "purchase_ticket", "environment_id"?: "kiosk_standard",
     "overrides": {"dexterity": "typical"}}

    Authenticated only -- the real AbilityProfile always comes from
    `request.user` (get_or_create_profile), never from a client-supplied
    user id or a client-supplied profile (section 15/16). Side-effect
    free: see api/services/what_if.py -- nothing here writes AbilityProfile,
    creates an InteractionSession, or persists anything at all.

    Requires consent, matching the existing standalone barrier/adaptation
    demo endpoints (DetectBarriersView._detect_standalone,
    RecommendAdaptationsView._recommend_standalone) this reuses the same
    engine as -- What-If is the same shape of request (profile + task +
    environment -> barriers + adaptations, no session), so it is held to
    the same "consent gates use of a profile for adaptation" rule they
    already are, not a new or looser one.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        task_id = request.data.get("task_id")
        environment_id = request.data.get("environment_id") or DEFAULT_ENVIRONMENT_ID
        overrides = request.data.get("overrides")

        if not task_id:
            return Response({"detail": "task_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        if not is_consented_for_adaptation(request.user):
            raise PermissionDenied("Consent required before AbilityOS can run a What-If simulation for this profile.")

        try:
            task_descriptor = get_task_descriptor(task_id)
        except TaskNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        try:
            environment_descriptor = EnvironmentAnalyzer.analyze_fixture(environment_id)
        except EnvironmentNotFoundError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

        profile = get_or_create_profile(request.user)

        try:
            result = run_what_if_simulation(profile, task_descriptor, environment_descriptor, overrides)
        except WhatIfValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(result)
