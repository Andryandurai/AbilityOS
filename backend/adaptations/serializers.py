from rest_framework import serializers

from adaptations.models import Adaptation, AdaptationResult


class AdaptationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adaptation
        fields = [
            "id",
            "name",
            "display_name",
            "description",
            "resolves_barrier_types",
            "modality",
            "accessibility_benefit",
            "interaction_cost",
            "risk",
            "risk_level",
            "requires_confirmation",
            "allowed_for_tasks",
            "ui_effects",
            "enabled",
        ]


class AdaptationResultSerializer(serializers.ModelSerializer):
    adaptation = AdaptationSerializer(read_only=True)
    barrier_type = serializers.CharField(source="barrier.barrier_type", read_only=True)

    class Meta:
        model = AdaptationResult
        fields = [
            "id",
            "session",
            "barrier",
            "barrier_type",
            "adaptation",
            "score",
            "score_breakdown",
            "rationale",
            "source",
            "candidates_considered",
            "approved",
            "requires_confirmation",
            "confirmed",
            "applied",
            "created_at",
        ]
