from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from abilities.serializers import AbilityProfileSerializer
from abilities.services.profile_service import (
    ProfileValidationError,
    apply_manual_update,
    clear_profile,
    get_or_create_profile,
)
from users.models import User
from users.services.ownership import assert_owner


def _assert_ownership(request, user_id):
    assert_owner(request, user_id, "You may only edit your own Ability Profile.")


class AbilityProfileView(APIView):
    """GET/PATCH/DELETE /api/users/{id}/ability-profile/ (Phase 2 section 12).

    Views stay thin — all the validation and "manual beats inferred beats
    default" logic lives in abilities.services.profile_service.
    """

    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        profile = get_or_create_profile(user)
        return Response(AbilityProfileSerializer(profile).data)

    def patch(self, request, user_id):
        _assert_ownership(request, user_id)
        user = get_object_or_404(User, pk=user_id)
        profile = get_or_create_profile(user)

        if "label" in request.data:
            profile.label = request.data["label"]
            profile.save(update_fields=["label"])

        try:
            apply_manual_update(
                profile,
                dimensions=request.data.get("dimensions"),
                preferred_modality=request.data.get("preferred_modality"),
                preferences=request.data.get("preferences"),
            )
        except ProfileValidationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(AbilityProfileSerializer(profile).data)

    def delete(self, request, user_id):
        """Phase 2 section 22 ("Clear Profile"): resets functional values to
        their defaults. The user account itself is never deleted here."""

        _assert_ownership(request, user_id)
        user = get_object_or_404(User, pk=user_id)
        profile = get_or_create_profile(user)
        clear_profile(profile)
        return Response(AbilityProfileSerializer(profile).data)
