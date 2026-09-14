"""Central DRF exception handler so orchestrator/service errors and AI
failures never surface as an unhandled 500 during a live demo (Part 37)."""

from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from api.services.orchestrator import OrchestratorError


def abilityos_exception_handler(exc, context):
    if isinstance(exc, OrchestratorError):
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    response = exception_handler(exc, context)
    if response is not None:
        return response

    return Response(
        {"detail": f"Unexpected server error: {exc}"},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
