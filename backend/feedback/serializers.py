from rest_framework import serializers

from feedback.models import Feedback, InteractionEvent, InteractionSession


class InteractionSessionSerializer(serializers.ModelSerializer):
    task_id = serializers.CharField(source="task.task_id", read_only=True)
    environment_id = serializers.CharField(
        source="environment.environment_id", read_only=True, default=None
    )
    experience_mode = serializers.CharField(read_only=True)
    completion_time_ms = serializers.IntegerField(read_only=True)

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
            "experience_mode",
            "assistance_count",
            "completed_at",
            "completion_time_ms",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "ai_used", "created_at", "updated_at", "completed_at"]


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
            "ease_rating",
            "adaptation_helpfulness",
            "optional_comment",
            "created_at",
        ]
        read_only_fields = ["id", "session", "created_at"]


class InteractionEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = InteractionEvent
        fields = ["id", "session", "step", "event_type", "control_id", "metadata", "created_at"]
        read_only_fields = ["id", "session", "created_at"]
