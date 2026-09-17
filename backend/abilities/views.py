from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from abilities.serializers import (
    AbilityProfileSerializer,
    UserProfileSelectionInputSerializer,
    UserProfileSelectionSerializer,
)
from abilities.services import selection_service
from abilities.services.profile_service import (
    ProfileValidationError,
    apply_manual_update,
    clear_profile,
    get_or_create_profile,
)
from abilities.services.suggestion_service import list_all_profiles, suggest_profiles
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
        # Phase 1 (Real User Authentication) section 11: previously no
        # ownership check at all here (PATCH/DELETE already had one via
        # _assert_ownership). assert_owner() is a no-op for an
        # unauthenticated caller, so this changes nothing for the
        # anonymous demo path -- it closes a real gap for authenticated
        # callers, where User A's token could have read User B's full
        # Ability Profile.
        _assert_ownership(request, user_id)
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


class ProfileSuggestionsView(APIView):
    """GET /api/users/{id}/profile-suggestions/ (Phase 3).

    Read-only and side-effect free: computing suggestions never writes a
    UserProfileSelection row or touches AbilityProfile (section 14/27) --
    a row is only ever created by an explicit POST to
    ProfileSelectionsView. Requires authentication (unlike
    AbilityProfileView/ConsentView, which stay anonymous-compatible for
    the pre-existing demo flow): nothing in the real onboarding journey
    this endpoint serves ever needs anonymous access, so there is no
    legacy behaviour to preserve here.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        assert_owner(request, user_id, "You may only view your own profile suggestions.")
        user = get_object_or_404(User, pk=user_id)
        profile = get_or_create_profile(user)
        return Response(
            {"suggestions": suggest_profiles(profile.dimensions), "all_profiles": list_all_profiles()}
        )


class ProfileSelectionsView(APIView):
    """GET/POST /api/users/{id}/profile-selections/ (Phase 3).

    POST is an upsert (Phase 3 section 9's uniqueness constraint on
    (user, profile_key) is enforced at the model level; this view's job is
    just to route request.user's own id through it, never a client-
    supplied one). Creating/updating a selection never touches
    AbilityProfile -- see docs/PROFILE_SUGGESTIONS.md's mutation rule.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        assert_owner(request, user_id, "You may only view your own profile selections.")
        user = get_object_or_404(User, pk=user_id)
        selections = selection_service.list_selections(user)
        return Response(UserProfileSelectionSerializer(selections, many=True).data)

    def post(self, request, user_id):
        assert_owner(request, user_id, "You may only change your own profile selections.")
        user = get_object_or_404(User, pk=user_id)
        serializer = UserProfileSelectionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        selection = selection_service.upsert_selection(
            user, serializer.validated_data["profile_key"], serializer.validated_data["status"]
        )
        return Response(UserProfileSelectionSerializer(selection).data, status=status.HTTP_200_OK)


class ProfileSelectionDetailView(APIView):
    """DELETE /api/users/{id}/profile-selections/{profile_key}/ (Phase 3
    section 13/26) — removes one selection row entirely, distinct from
    "reject" (section 20: rejecting keeps the record, with
    status=rejected)."""

    permission_classes = [IsAuthenticated]

    def delete(self, request, user_id, profile_key):
        assert_owner(request, user_id, "You may only change your own profile selections.")
        user = get_object_or_404(User, pk=user_id)
        deleted = selection_service.delete_selection(user, profile_key)
        if not deleted:
            return Response({"detail": "No selection found for this profile."}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
