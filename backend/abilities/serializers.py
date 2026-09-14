from rest_framework import serializers

from abilities.models import DIMENSION_KEYS, AbilityProfile


class AbilityProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = AbilityProfile
        fields = [
            "id",
            "user_id",
            "username",
            "label",
            "dimensions",
            "preferred_modality",
            "preferences",
            "updated_at",
        ]
        read_only_fields = ["id", "user_id", "username", "updated_at"]

    def validate_dimensions(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError("dimensions must be an object.")
        for key, val in value.items():
            if key not in DIMENSION_KEYS:
                raise serializers.ValidationError(f"Unknown ability dimension '{key}'.")
            if not isinstance(val, dict) or "level" not in val:
                raise serializers.ValidationError(f"Dimension '{key}' must include a 'level'.")
        return value
