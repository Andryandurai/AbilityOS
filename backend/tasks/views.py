from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from tasks.models import Task
from tasks.serializers import TaskSerializer
from tasks.services.task_service import TaskNotFoundError, get_task_descriptor


class TaskViewSet(ReadOnlyModelViewSet):
    """GET /api/tasks/ and GET /api/tasks/{id}/ (Part 11)."""

    queryset = Task.objects.all().prefetch_related("steps")
    serializer_class = TaskSerializer
    permission_classes = [AllowAny]
    lookup_field = "task_id"


@api_view(["POST"])
@permission_classes([AllowAny])
def analyze_task(request):
    """POST /api/tasks/analyze/ — {"task_id": "purchase_ticket"} -> TaskDescriptor.

    Phase 3's Task Understanding Engine entry point. Deterministic lookup
    only (tasks.services.task_service) — no AI, no barrier detection, no
    accessibility judgement. Returns 400 for a malformed request and 404
    for an unknown task_id; never silently invents a task.
    """

    task_id = request.data.get("task_id")
    if not task_id:
        return Response({"detail": "task_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        descriptor = get_task_descriptor(task_id)
    except TaskNotFoundError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)

    return Response(descriptor)
