from rest_framework import serializers

from barriers.models import Barrier


class BarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Barrier
        fields = [
            "id",
            "session",
            "barrier_type",
            "ability_dimension",
            "severity",
            "confidence",
            "evidence",
            "created_at",
        ]
