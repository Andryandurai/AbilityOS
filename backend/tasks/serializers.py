from rest_framework import serializers

from tasks.models import Task, TaskStep


class TaskStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStep
        fields = ["step_id", "order", "name", "controls"]


class TaskSerializer(serializers.ModelSerializer):
    steps = TaskStepSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = ["id", "task_id", "name", "description", "steps"]
