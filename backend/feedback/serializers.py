from rest_framework import serializers

from feedback.models import Feedback, InteractionSession


class InteractionSessionSerializer(serializers.ModelSerializer):
    task_id = serializers.CharField(source="task.task_id", read_only=True)
    environment_id = serializers.CharField(
        source="environment.environment_id", read_only=True, default=None
    )

    class Meta:
        model = InteractionSession
        fields = [
            "id",
            "user",
            "task",
            "task_id",
            "environment",
            "environment_id",
            "status",
            "ai_used",
            "baseline_mode",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "ai_used", "created_at", "updated_at"]


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = [
            "id",
            "session",
            "completed",
            "errors",
            "time_seconds",
            "assistance_requested",
            "effort",
            "confidence",
            "created_at",
        ]
        read_only_fields = ["id", "session", "created_at"]
