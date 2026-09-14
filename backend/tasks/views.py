from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ReadOnlyModelViewSet

from tasks.models import Task
from tasks.serializers import TaskSerializer


class TaskViewSet(ReadOnlyModelViewSet):
    """GET /api/tasks/ and GET /api/tasks/{id}/ (Part 11)."""

    queryset = Task.objects.all().prefetch_related("steps")
    serializer_class = TaskSerializer
    permission_classes = [AllowAny]
    lookup_field = "task_id"
