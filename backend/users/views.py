from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from users.models import User
from users.serializers import AbilityOSTokenObtainPairSerializer, ConsentSerializer, UserSerializer
from users.services import consent_service
from users.services.ownership import assert_owner


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ — {"username": ..., "password": ...}."""

    serializer_class = AbilityOSTokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_scope = "auth_login"


@api_view(["GET"])
@permission_classes([AllowAny])
def list_demo_users(request):
    """GET /api/users/demo/ — the pre-seeded personas the kiosk demo switches
    between (Part 13/15). Not part of the core spec's endpoint list, but
    required for the "select an Ability Profile" step of the demo flow."""

    users = User.objects.filter(is_demo_profile=True).order_by("id")
    return Response(UserSerializer(users, many=True).data)


class ConsentView(APIView):
    """GET/POST /api/users/{id}/consent/ (Phase 2 section 2)."""

    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        record = consent_service.get_or_create_consent(user)
        return Response(ConsentSerializer(record).data)

    def post(self, request, user_id):
        assert_owner(request, user_id, "You may only change your own consent.")
        user = get_object_or_404(User, pk=user_id)

        granted = bool(request.data.get("granted", True))
        scope = request.data.get("scope")

        if granted:
            record = consent_service.grant_consent(user, scope=scope)
        else:
            record = consent_service.revoke_consent(user)

        return Response(ConsentSerializer(record).data)
