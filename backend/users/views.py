from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from users.models import User
from users.serializers import (
    AbilityOSTokenObtainPairSerializer,
    ConsentSerializer,
    MeSerializer,
    RegisterSerializer,
    UserSerializer,
)
from users.services import consent_service
from users.services.ownership import assert_owner


class LoginView(TokenObtainPairView):
    """POST /api/auth/login/ — {"username": ..., "password": ...}."""

    serializer_class = AbilityOSTokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_scope = "auth_login"


class RegisterView(APIView):
    """POST /api/auth/register/ — Phase 1 (Real User Authentication).

    Creates a real, non-demo account (`is_demo_profile=False`, enforced in
    RegisterSerializer.create() regardless of what the request sends) and
    nothing else: no AbilityProfile is eagerly created (AbilityProfileView
    already lazily creates one via get_or_create_profile on first access —
    this endpoint doesn't need to duplicate that), no consent is granted,
    no demo persona is assigned. Registration only proves an account exists
    and can then log in via the existing POST /api/auth/login/.
    """

    permission_classes = [AllowAny]
    throttle_scope = "auth_register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class MeView(APIView):
    """GET /api/auth/me/ — Phase 1 section 7.

    Identity comes from `request.user` only -- never from a URL/body/query
    user id -- so this endpoint can never be used to read someone else's
    account by guessing an id. Returns no password, hash, or token.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)


class LogoutView(APIView):
    """POST /api/auth/logout/ — {"refresh": "<refresh token>"}.

    Requires authentication (a valid access token) and blacklists the
    supplied refresh token via SimpleJWT's token_blacklist app (enabled in
    config/settings.py for this phase), so that specific refresh token can
    never be used again to mint a new access token. This does NOT revoke
    the access token that was used to call this endpoint -- SimpleJWT
    access tokens are stateless/unrevocable by design, so the current
    access token remains valid (able to authenticate requests) until it
    naturally expires (ACCESS_TOKEN_LIFETIME, see settings.py). The
    frontend is responsible for discarding both tokens from its own storage
    on logout (see useAuth.js) -- that combination (refresh blacklisted +
    access discarded client-side) is what "logged out" means in this
    implementation; it is not a claim that the access token itself is
    invalidated server-side. See docs/AUTHENTICATION.md.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            raise ValidationError({"refresh": "This field is required."})
        try:
            token = RefreshToken(refresh)
            token.blacklist()
        except TokenError as exc:
            raise ValidationError({"refresh": str(exc)}) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([AllowAny])
def list_demo_users(request):
    """GET /api/users/demo/ — the pre-seeded personas the kiosk demo switches
    between (Part 13/15). Not part of the core spec's endpoint list, but
    required for the "select an Ability Profile" step of the demo flow."""

    users = User.objects.filter(is_demo_profile=True).order_by("id")
    return Response(UserSerializer(users, many=True).data)


class ConsentView(APIView):
    """GET/POST /api/users/{id}/consent/ (Phase 2 section 2).

    Phase 1 (Real User Authentication) section 11: GET previously had no
    ownership check at all (POST already had one). assert_owner() is a
    no-op for an unauthenticated caller (see ownership.py), so adding it
    here changes nothing for the anonymous demo path -- it only starts
    mattering now that a real, authenticated caller exists, closing a real
    gap where User A's token could have read User B's consent record.
    """

    permission_classes = [AllowAny]

    def get(self, request, user_id):
        assert_owner(request, user_id, "You may only view your own consent.")
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
