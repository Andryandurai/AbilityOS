"""Central DRF exception handler so orchestrator/service errors and AI
failures never surface as an unhandled 500 during a live demo (Part 37).

Phase 8 section 20/27/29: an unexpected error is always logged server-side
(it was previously silent — invisible to both the console and any log
aggregator) and the client only ever sees the raw exception text in DEBUG
mode. In a real deployment (DEBUG=False) it gets a generic message instead
— the detail stays in the server log, not the HTTP response, so a database
error or similar never leaks internal detail to whoever is looking at the
browser's network tab.
"""

from __future__ import annotations

import logging

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from api.services.orchestrator import OrchestratorError

logger = logging.getLogger("api")


def abilityos_exception_handler(exc, context):
    if isinstance(exc, OrchestratorError):
        return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

    response = exception_handler(exc, context)
    if response is not None:
        return response

    logger.exception("Unhandled exception in %s", context.get("view"), exc_info=exc)
    message = f"Unexpected server error: {exc}" if settings.DEBUG else "Unexpected server error. Please try again."
    return Response({"detail": message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
