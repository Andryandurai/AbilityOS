from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from users.models import ConsentRecord, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "display_name", "is_demo_profile"]


class MeSerializer(serializers.ModelSerializer):
    """GET /api/auth/me/'s response shape -- kept separate from
    UserSerializer (used by login/list-demo-users) rather than adding
    `email` there, so existing response shapes are not changed for
    endpoints unrelated to this phase."""

    class Meta:
        model = User
        fields = ["id", "username", "email", "display_name", "is_demo_profile"]


class RegisterSerializer(serializers.Serializer):
    """POST /api/auth/register/'s input contract.

    A plain Serializer, not a ModelSerializer: registration needs its own
    rules (password + password_confirm, a plaintext password that must
    never reach User.objects.create() directly) that don't map cleanly onto
    a model field set, and abilities/services/profile_service.py already
    establishes the pattern in this codebase of keeping such validation
    explicit and readable rather than inferred from model introspection.
    """

    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    display_name = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("An account with this username already exists.")
        return value

    def validate_email(self, value):
        # The model field itself is not unique (existing demo personas
        # carry no email at all), so this is an application-level rule for
        # new registrations only, not a database constraint -- no
        # migration, no risk of colliding with existing seeded data.
        if value and User.objects.filter(email__iexact=value).exclude(email="").exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate_password(self, value):
        # Reuses AUTH_PASSWORD_VALIDATORS (config/settings.py) -- the same
        # rules any other Django-managed password already has to satisfy,
        # not a new, separately-invented policy.
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        user = User(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            display_name=validated_data.get("display_name", ""),
            is_demo_profile=False,
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


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
