from django.urls import include, path
from rest_framework.routers import DefaultRouter

from abilities.views import (
    AbilityProfileView,
    ProfileSelectionDetailView,
    ProfileSelectionsView,
    ProfileSuggestionsView,
)
from adaptations.views import adaptation_candidates
from analytics.views import adaptations as analytics_adaptations
from analytics.views import barriers as analytics_barriers
from analytics.views import before_after, dashboard
from analytics.views import sessions as analytics_sessions
from api import views as orchestrator_views
from questionnaire.views import (
    CompleteQuestionnaireView,
    ConfirmQuestionnaireView,
    QuestionnaireResponseView,
    QuestionnaireView,
    StartQuestionnaireView,
)
from tasks.views import TaskViewSet, analyze_task
from users.views import ConsentView, LoginView, LogoutView, MeView, RegisterView, list_demo_users

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
    # Phase 1 (Real User Authentication): register/me/logout are additive --
    # every existing anonymous-compatible endpoint above and below is
    # unchanged.
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("users/demo/", list_demo_users, name="demo-users"),
    path("users/<int:user_id>/ability-profile/", AbilityProfileView.as_view(), name="ability-profile"),
    path("users/<int:user_id>/consent/", ConsentView.as_view(), name="consent"),
    # --- Phase 3: Profile Suggestions & User Profile Selection -------------------
    path(
        "users/<int:user_id>/profile-suggestions/",
        ProfileSuggestionsView.as_view(),
        name="profile-suggestions",
    ),
    path(
        "users/<int:user_id>/profile-selections/",
        ProfileSelectionsView.as_view(),
        name="profile-selections",
    ),
    path(
        "users/<int:user_id>/profile-selections/<str:profile_key>/",
        ProfileSelectionDetailView.as_view(),
        name="profile-selection-detail",
    ),
    # --- Phase 2: Onboarding, Consent & Questionnaire ----------------------------
    path("questionnaire/", QuestionnaireView.as_view(), name="questionnaire"),
    path("questionnaire/start/", StartQuestionnaireView.as_view(), name="questionnaire-start"),
    path(
        "questionnaire/<int:session_id>/response/",
        QuestionnaireResponseView.as_view(),
        name="questionnaire-response",
    ),
    path(
        "questionnaire/<int:session_id>/complete/",
        CompleteQuestionnaireView.as_view(),
        name="questionnaire-complete",
    ),
    path(
        "questionnaire/<int:session_id>/confirm/",
        ConfirmQuestionnaireView.as_view(),
        name="questionnaire-confirm",
    ),
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
    # --- Phase 6: Feedback + History + Analytics Integration ----------------------
    path("users/<int:user_id>/sessions/", orchestrator_views.UserSessionsView.as_view(), name="user-sessions"),
    # --- Phase 7: Advanced Adaptive Intelligence & What-If Simulation -------------
    path("what-if/simulate/", orchestrator_views.WhatIfSimulateView.as_view(), name="what-if-simulate"),
    # --- Analytics ----------------------------------------------------------------
    path("analytics/before-after/", before_after, name="analytics-before-after"),
    path("analytics/dashboard/", dashboard, name="analytics-dashboard"),
    path("analytics/adaptations/", analytics_adaptations, name="analytics-adaptations"),
    path("analytics/barriers/", analytics_barriers, name="analytics-barriers"),
    path("analytics/sessions/", analytics_sessions, name="analytics-sessions"),
]
