from django.urls import include, path
from rest_framework.routers import DefaultRouter

from abilities.views import AbilityProfileView
from adaptations.views import adaptation_candidates
from analytics.views import adaptations as analytics_adaptations
from analytics.views import barriers as analytics_barriers
from analytics.views import before_after, dashboard
from analytics.views import sessions as analytics_sessions
from api import views as orchestrator_views
from tasks.views import TaskViewSet, analyze_task
from users.views import ConsentView, LoginView, list_demo_users

router = DefaultRouter()
router.register(r"tasks", TaskViewSet, basename="task")

urlpatterns = [
    # NOTE: explicit routes that could collide with the DRF router's
    # tasks/<task_id>/ detail lookup (e.g. "analyze" being a valid slug)
    # must be listed before `include(router.urls)` — Django resolves
    # urlpatterns in order, first match wins.
    path("tasks/analyze/", analyze_task, name="tasks-analyze"),
    path("", include(router.urls)),
    # --- Foundation (Phase 1) ------------------------------------------------------
    path("health/", orchestrator_views.health, name="health"),
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
    # --- Phase 7: step-level tracking + explicit lifecycle -----------------------
    path(
        "interactions/<int:session_id>/events/",
        orchestrator_views.RecordEventsView.as_view(),
        name="interaction-events",
    ),
    path(
        "interactions/<int:session_id>/complete/",
        orchestrator_views.CompleteInteractionView.as_view(),
        name="interaction-complete",
    ),
    path(
        "interactions/<int:session_id>/abandon/",
        orchestrator_views.AbandonInteractionView.as_view(),
        name="interaction-abandon",
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
    path("analytics/adaptations/", analytics_adaptations, name="analytics-adaptations"),
    path("analytics/barriers/", analytics_barriers, name="analytics-barriers"),
    path("analytics/sessions/", analytics_sessions, name="analytics-sessions"),
]
