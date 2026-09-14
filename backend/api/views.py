"""Orchestrator-backed endpoints — one per stage of the Part 5 workflow.

Views stay thin: validate input, delegate to InteractionOrchestrator, shape
the response. All the actual reasoning lives in the app-level services.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from adaptations.serializers import AdaptationResultSerializer
from api.services.orchestrator import InteractionOrchestrator
from barriers.serializers import BarrierSerializer
from environments.serializers import EnvironmentSerializer
from feedback.models import InteractionSession
from feedback.serializers import FeedbackSerializer
from users.models import User


class StartInteractionView(APIView):
    """POST /api/interactions/start/ — {"user_id", "task_id", "environment_id"?, "baseline_mode"?}."""

    permission_classes = [AllowAny]

    def post(self, request):
        user = get_object_or_404(User, pk=request.data.get("user_id"))
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
    """POST /api/environment/analyze/ — {"session_id", "image_base64"?}."""

    permission_classes = [AllowAny]

    def post(self, request):
        session = get_object_or_404(InteractionSession, pk=request.data.get("session_id"))
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
    """POST /api/barriers/detect/ — {"session_id"}."""

    permission_classes = [AllowAny]

    def post(self, request):
        session = get_object_or_404(InteractionSession, pk=request.data.get("session_id"))
        barriers = InteractionOrchestrator.detect_barriers(session)
        return Response({"barriers": BarrierSerializer(barriers, many=True).data})


class RecommendAdaptationsView(APIView):
    """POST /api/adaptations/recommend/ — {"session_id"}."""

    permission_classes = [AllowAny]

    def post(self, request):
        session = get_object_or_404(InteractionSession, pk=request.data.get("session_id"))
        results = InteractionOrchestrator.recommend_adaptations(session)
        return Response(
            {
                "ai_used": session.ai_used,
                "results": AdaptationResultSerializer(results, many=True).data,
            }
        )


class ApplyAdaptationView(APIView):
    """POST /api/interactions/{id}/apply/ — {"confirmed_ids"?: [1, 2]}."""

    permission_classes = [AllowAny]

    def post(self, request, session_id):
        session = get_object_or_404(InteractionSession, pk=session_id)
        payload = InteractionOrchestrator.apply(session, confirmed_ids=request.data.get("confirmed_ids"))
        return Response(payload)


class InteractionFeedbackView(APIView):
    """POST /api/interactions/{id}/feedback/."""

    permission_classes = [AllowAny]

    def post(self, request, session_id):
        session = get_object_or_404(InteractionSession, pk=session_id)
        feedback = InteractionOrchestrator.record_feedback(session, request.data)
        return Response(
            {"status": "recorded", "profile_updated": True, "feedback": FeedbackSerializer(feedback).data}
        )


class InteractionSummaryView(APIView):
    """GET /api/interactions/{id}/summary/ — full developer-panel payload."""

    permission_classes = [AllowAny]

    def get(self, request, session_id):
        session = get_object_or_404(InteractionSession, pk=session_id)
        return Response(InteractionOrchestrator.summary(session))
