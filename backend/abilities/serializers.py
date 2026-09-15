from rest_framework import serializers

from abilities.models import AbilityProfile


class AbilityProfileSerializer(serializers.ModelSerializer):
    """Read-shape for the Ability Profile API.

    Validation of incoming writes is not this serializer's job — the view
    delegates directly to abilities.services.profile_service, which is the
    single source of truth for the controlled vocabulary (level/confidence/
    source rules). Keeping validation in one place avoids the two layers
    silently drifting apart.
    """

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
        read_only_fields = fields
