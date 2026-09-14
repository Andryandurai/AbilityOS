from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from abilities.models import AbilityProfile
from abilities.serializers import AbilityProfileSerializer
from users.models import User


class AbilityProfileView(APIView):
    """GET/PATCH /api/users/{id}/ability-profile/ (Part 11).

    Manual edits always take priority over inferred values (Part 20) — a
    PATCH here simply overwrites whichever dimensions are supplied, tagging
    them with source='manual' unless the caller says otherwise.
    """

    permission_classes = [AllowAny]

    def get(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        profile, _ = AbilityProfile.objects.get_or_create(user=user)
        return Response(AbilityProfileSerializer(profile).data)

    def patch(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        profile, _ = AbilityProfile.objects.get_or_create(user=user)

        incoming_dims = request.data.get("dimensions")
        if incoming_dims:
            merged = dict(profile.dimensions)
            for key, val in incoming_dims.items():
                val.setdefault("source", "manual")
                val.setdefault("confidence", 0.9)
                merged[key] = val
            profile.dimensions = merged

        for field in ("label", "preferred_modality", "preferences"):
            if field in request.data:
                setattr(profile, field, request.data[field])

        profile.save()
        return Response(AbilityProfileSerializer(profile).data)
