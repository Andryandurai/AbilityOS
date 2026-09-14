from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from users.models import ConsentRecord, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "display_name", "is_demo_profile"]


class AbilityOSTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Login endpoint (Part 11 POST /api/auth/login/) that also returns the
    user record, so the frontend can immediately show "who is signed in"
    without a second round trip."""

    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


class ConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = ["id", "user", "granted", "scope", "granted_at", "updated_at"]
        read_only_fields = ["id", "user", "updated_at"]
