from django.urls import include, path
from rest_framework.routers import DefaultRouter

from abilities.views import AbilityProfileView
from adaptations.views import adaptation_candidates
from analytics.views import before_after, dashboard
from api import views as orchestrator_views
from tasks.views import TaskViewSet
from users.views import ConsentView, LoginView, list_demo_users

router = DefaultRouter()
router.register(r"tasks", TaskViewSet, basename="task")

urlpatterns = [
    path("", include(router.urls)),
    # --- Users / auth / consent -------------------------------------------------
    path("auth/login/", LoginView.as_view(), name="login"),
    path("users/demo/", list_demo_users, name="demo-users"),
    path("users/<int:user_id>/ability-profile/", AbilityProfileView.as_view(), name="ability-profile"),
    path("users/<int:user_id>/consent/", ConsentView.as_view(), name="consent"),
    # --- Core AbilityOS workflow (Part 5 / Part 11) ------------------------------
    path("interactions/start/", orchestrator_views.StartInteractionView.as_view(), name="interaction-start"),
    path("environment/analyze/", orchestrator_views.AnalyzeEnvironmentView.as_view(), name="environment-analyze"),
    path("barriers/detect/", orchestrator_views.DetectBarriersView.as_view(), name="barriers-detect"),
    path("adaptations/candidates/", adaptation_candidates, name="adaptation-candidates"),
    path(
        "adaptations/recommend/",
        orchestrator_views.RecommendAdaptationsView.as_view(),
        name="adaptations-recommend",
    ),
    path(
        "interactions/<int:session_id>/apply/",
        orchestrator_views.ApplyAdaptationView.as_view(),
        name="interaction-apply",
    ),
    path(
        "interactions/<int:session_id>/feedback/",
        orchestrator_views.InteractionFeedbackView.as_view(),
        name="interaction-feedback",
    ),
    path(
        "interactions/<int:session_id>/summary/",
        orchestrator_views.InteractionSummaryView.as_view(),
        name="interaction-summary",
    ),
    # --- Analytics ----------------------------------------------------------------
    path("analytics/before-after/", before_after, name="analytics-before-after"),
    path("analytics/dashboard/", dashboard, name="analytics-dashboard"),
]
