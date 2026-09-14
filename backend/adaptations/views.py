from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from adaptations.models import Adaptation
from adaptations.serializers import AdaptationSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def adaptation_candidates(request):
    """GET /api/adaptations/candidates/?barrier_type=small_tap_targets

    Returns the raw catalogue entries that *could* resolve a barrier type,
    without running the scoring/AI pipeline — useful for the developer
    panel to show "here is the full candidate list" (Part 15 step 6)
    independently of a live session.
    """

    barrier_type = request.query_params.get("barrier_type")
    qs = Adaptation.objects.filter(enabled=True)
    if barrier_type:
        qs = [a for a in qs if barrier_type in a.resolves_barrier_types]
    return Response(AdaptationSerializer(qs, many=True).data)
