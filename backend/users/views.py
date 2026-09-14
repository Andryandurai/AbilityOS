from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from users.models import ConsentRecord, User
from users.serializers import AbilityOSTokenObtainPairSerializer, ConsentSerializer, UserSerializer


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ — {"username": ..., "password": ...}."""

    serializer_class = AbilityOSTokenObtainPairSerializer
    permission_classes = [AllowAny]


@api_view(["GET"])
@permission_classes([AllowAny])
def list_demo_users(request):
    """GET /api/users/demo/ — the pre-seeded personas the kiosk demo switches
    between (Part 13/15). Not part of the core spec's endpoint list, but
    required for the "select an Ability Profile" step of the demo flow."""

    users = User.objects.filter(is_demo_profile=True).order_by("id")
    return Response(UserSerializer(users, many=True).data)


class ConsentView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, user_id):
        record, _ = ConsentRecord.objects.get_or_create(user_id=user_id)
        return Response(ConsentSerializer(record).data)

    def post(self, request, user_id):
        from django.utils import timezone

        record, _ = ConsentRecord.objects.get_or_create(user_id=user_id)
        granted = bool(request.data.get("granted", True))
        scope = request.data.get("scope", ["interaction_adaptation"])
        record.granted = granted
        record.scope = scope
        record.granted_at = timezone.now() if granted else None
        record.save()
        return Response(ConsentSerializer(record).data, status=status.HTTP_200_OK)
