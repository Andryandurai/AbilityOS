"""Phase 2 (Onboarding, Consent & Questionnaire) API views.

Views stay thin -- validate/authorize, delegate to
questionnaire.services.questionnaire_service, shape the response. Mirrors
the existing api/views.py convention in this codebase.
"""

from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from abilities.serializers import AbilityProfileSerializer
from questionnaire.models import QuestionnaireSession
from questionnaire.serializers import QuestionnaireQuestionSerializer, QuestionnaireResponseInputSerializer
from questionnaire.services import questionnaire_service as svc
from users.services.consent_service import is_consented_for_adaptation


def _owned_session(request, session_id) -> QuestionnaireSession:
    """Phase 2 section 25/26: ownership is enforced here, once, for every
    session-scoped view below -- never inferred from a client-supplied
    user id. `staff` gets the same allowance assert_owner() (users/
    services/ownership.py) already gives every other owned resource in
    this codebase, for consistency rather than inventing a second rule."""

    session = get_object_or_404(QuestionnaireSession, pk=session_id)
    if session.user_id != request.user.id and not request.user.is_staff:
        raise PermissionDenied("You may only access your own questionnaire session.")
    return session


class QuestionnaireView(APIView):
    """GET /api/questionnaire/ — the current question set. Public: this is
    reference data (question text/options), not personal information, the
    same category of fact as the barrier/adaptation catalogues elsewhere
    in this API."""

    permission_classes = [AllowAny]

    def get(self, request):
        version, questions = svc.get_questionnaire()
        return Response(
            {"version": version, "questions": QuestionnaireQuestionSerializer(questions, many=True).data}
        )


class StartQuestionnaireView(APIView):
    """POST /api/questionnaire/start/ — creates a session for
    request.user. Consent is checked here, once, at the natural entry
    point (Phase 2 section 15): no session exists without it, so no
    response/complete/confirm call is ever reachable without it either."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "session_start"

    def post(self, request):
        if not is_consented_for_adaptation(request.user):
            raise PermissionDenied(
                "Consent is required before AbilityOS can use your answers to personalize interactions."
            )
        session = svc.start_questionnaire(request.user)
        return Response({"session_id": session.id, "version": session.version}, status=status.HTTP_201_CREATED)


class QuestionnaireResponseView(APIView):
    """POST /api/questionnaire/{id}/response/ — {"question_id", "selected_value"}."""

    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = _owned_session(request, session_id)
        serializer = QuestionnaireResponseInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            response = svc.save_response(
                session, serializer.validated_data["question_id"], serializer.validated_data["selected_value"]
            )
        except svc.QuestionnaireError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"question_id": response.question_id, "selected_value": response.selected_value})


class CompleteQuestionnaireView(APIView):
    """POST /api/questionnaire/{id}/complete/ — validates every answer and
    returns the generated `dimensions`, WITHOUT writing to AbilityProfile
    (Phase 2 section 14/21 -- see docs/QUESTIONNAIRE.md for why a separate
    confirm step exists). Idempotent: calling this again on an
    already-completed session just re-returns the same generated
    dimensions."""

    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = _owned_session(request, session_id)
        try:
            dimensions = svc.complete_questionnaire(session)
        except svc.QuestionnaireError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"session_id": session.id, "dimensions": dimensions, "completed_at": session.completed_at})


class ConfirmQuestionnaireView(APIView):
    """POST /api/questionnaire/{id}/confirm/ — the one endpoint in this
    app that writes to AbilityProfile, exclusively via
    abilities.services.profile_service.apply_manual_update(). Requires the
    session to already be completed; `dimensions` is always re-derived
    server-side from the stored responses, never accepted from the
    request body."""

    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        session = _owned_session(request, session_id)
        try:
            profile = svc.confirm_questionnaire(session)
        except svc.QuestionnaireError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AbilityProfileSerializer(profile).data)
