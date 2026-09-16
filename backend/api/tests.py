from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from adaptations.models import Adaptation, AdaptationResult
from api.services.orchestrator import InteractionOrchestrator
from barriers.models import Barrier
from feedback.models import InteractionSession
from tasks.models import Task, TaskStep
from users.models import User


class HealthCheckTests(TestCase):
    """Phase 1 foundation check: React -> Django -> Database actually works."""

    def test_health_endpoint_reports_database_connected(self):
        client = APIClient()
        response = client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        self.assertTrue(response.data["database"]["connected"])
        self.assertIn(response.data["database"]["engine"], ["postgresql", "sqlite"])

    def test_health_endpoint_reports_ai_configuration_state(self):
        client = APIClient()
        response = client.get("/api/health/")
        self.assertIn("ai_decision_engine", response.data)
        self.assertIn("configured", response.data["ai_decision_engine"])


class InteractionWorkflowTests(TestCase):
    """End-to-end tests of the orchestrated workflow via the real REST API —
    the same sequence of calls the React kiosk makes (Part 5 / Part 17)."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.low_vision_dexterity_user = User.objects.get(username="demo_low_vision_dexterity")
        self.cognitive_user = User.objects.get(username="demo_cognitive_load")
        self.hearing_user = User.objects.get(username="demo_hearing_difficulty")
        self.limited_mobility_reach_user = User.objects.get(username="demo_limited_mobility_reach")
        self.speech_difficulty_user = User.objects.get(username="demo_speech_difficulty")
        self.fatigue_reduced_stamina_user = User.objects.get(username="demo_fatigue_reduced_stamina")
        self.slower_reaction_speed_user = User.objects.get(username="demo_slower_reaction_speed")
        self.visual_hearing_support_user = User.objects.get(username="demo_visual_hearing_support")
        self.high_interaction_sensitivity_user = User.objects.get(username="demo_high_interaction_sensitivity")

    def _run_pipeline(self, user_id, baseline_mode=False):
        start = self.client.post(
            "/api/interactions/start/",
            {"user_id": user_id, "task_id": "purchase_ticket", "baseline_mode": baseline_mode},
            format="json",
        )
        self.assertEqual(start.status_code, 201)
        session_id = start.data["session_id"]

        env = self.client.post("/api/environment/analyze/", {"session_id": session_id}, format="json")
        self.assertEqual(env.status_code, 200)

        barriers = self.client.post("/api/barriers/detect/", {"session_id": session_id}, format="json")
        self.assertEqual(barriers.status_code, 200)

        recommend = self.client.post("/api/adaptations/recommend/", {"session_id": session_id}, format="json")
        self.assertEqual(recommend.status_code, 200)

        apply = self.client.post(f"/api/interactions/{session_id}/apply/", {}, format="json")
        self.assertEqual(apply.status_code, 200)

        return session_id, barriers.data, recommend.data, apply.data

    def test_low_vision_dexterity_profile_gets_target_size_and_contrast_adaptations(self):
        session_id, barriers, recommend, apply = self._run_pipeline(self.low_vision_dexterity_user.id)

        barrier_types = {b["barrier_type"] for b in barriers["barriers"]}
        self.assertIn("small_tap_targets", barrier_types)
        self.assertIn("low_contrast", barrier_types)

        applied_names = set(apply["applied_adaptations"])
        self.assertIn("increase_target_size", applied_names)
        self.assertIn("increase_contrast", applied_names)
        self.assertIn("button_scale", apply["ui_effects"])
        self.assertIn("contrast", apply["ui_effects"])

    def test_cognitive_load_profile_gets_step_by_step_flow(self):
        session_id, barriers, recommend, apply = self._run_pipeline(self.cognitive_user.id)

        barrier_types = {b["barrier_type"] for b in barriers["barriers"]}
        self.assertIn("too_many_choices", barrier_types)
        self.assertIn("step_by_step_flow", apply["applied_adaptations"])

    def test_hearing_difficulty_profile_gets_caption_audio(self):
        session_id, barriers, recommend, apply = self._run_pipeline(self.hearing_user.id)

        barrier_types = {b["barrier_type"] for b in barriers["barriers"]}
        self.assertIn("audio_only_alert", barrier_types)
        self.assertIn("caption_audio", apply["applied_adaptations"])

    def test_limited_mobility_reach_profile_gets_reachable_control_layout(self):
        session_id, barriers, recommend, apply = self._run_pipeline(self.limited_mobility_reach_user.id)

        barrier_types = {b["barrier_type"] for b in barriers["barriers"]}
        self.assertIn("controls_out_of_reach", barrier_types)
        self.assertIn("reachable_control_layout", apply["applied_adaptations"])
        self.assertIn("reachable_layout", apply["ui_effects"])

    def test_speech_difficulty_profile_gets_touch_text_alternative(self):
        session_id, barriers, recommend, apply = self._run_pipeline(self.speech_difficulty_user.id)

        barrier_types = {b["barrier_type"] for b in barriers["barriers"]}
        self.assertIn("voice_only_input", barrier_types)
        self.assertIn("touch_text_alternative", apply["applied_adaptations"])
        self.assertIn("touch_text_mode", apply["ui_effects"])

    def test_typical_profile_does_not_get_voice_only_input_barrier(self):
        """Negative case (section 21): the environment always offers the
        voice_destination control regardless of who's using the kiosk — a
        profile whose speech is typical must never see the barrier."""
        session_id, barriers, recommend, apply = self._run_pipeline(self.low_vision_dexterity_user.id)

        barrier_types = {b["barrier_type"] for b in barriers["barriers"]}
        self.assertNotIn("voice_only_input", barrier_types)
        self.assertNotIn("touch_text_alternative", apply["applied_adaptations"])

    def test_fatigue_reduced_stamina_profile_gets_streamline_task_flow(self):
        session_id, barriers, recommend, apply = self._run_pipeline(self.fatigue_reduced_stamina_user.id)

        barrier_types = {b["barrier_type"] for b in barriers["barriers"]}
        self.assertIn("excessive_interaction_burden", barrier_types)
        self.assertIn("streamline_task_flow", apply["applied_adaptations"])
        self.assertEqual(apply["ui_effects"]["flow"], "streamlined")

    def test_fresh_fatigue_profile_does_not_get_excessive_interaction_burden_barrier(self):
        """Negative case (section 21): the environment's flow length is the
        same for everyone — a profile whose fatigue/stamina is fresh/typical
        must never see the barrier or the streamlined-flow adaptation."""
        session_id, barriers, recommend, apply = self._run_pipeline(self.low_vision_dexterity_user.id)

        barrier_types = {b["barrier_type"] for b in barriers["barriers"]}
        self.assertNotIn("excessive_interaction_burden", barrier_types)
        self.assertNotIn("streamline_task_flow", apply["applied_adaptations"])

    def test_slower_reaction_speed_profile_gets_increase_interaction_timeout(self):
        session_id, barriers, recommend, apply = self._run_pipeline(self.slower_reaction_speed_user.id)

        barrier_types = {b["barrier_type"] for b in barriers["barriers"]}
        self.assertIn("time_limited_interaction", barrier_types)
        self.assertIn("increase_interaction_timeout", apply["applied_adaptations"])
        self.assertEqual(apply["ui_effects"]["extended_timeout_seconds"], 20)

    def test_typical_reaction_speed_profile_does_not_get_time_limited_interaction_barrier(self):
        """Negative case (section 26, CASE 1): the environment's confirmation
        window is the same for everyone — a profile whose reaction speed is
        typical must never see the barrier or the timeout-extension
        adaptation."""
        session_id, barriers, recommend, apply = self._run_pipeline(self.low_vision_dexterity_user.id)

        barrier_types = {b["barrier_type"] for b in barriers["barriers"]}
        self.assertNotIn("time_limited_interaction", barrier_types)
        self.assertNotIn("increase_interaction_timeout", apply["applied_adaptations"])

    def test_visual_hearing_support_profile_gets_both_barriers_and_adaptations(self):
        """TEST 1 + TEST 2 (Phase 5 section 17): both a real audio-only
        mismatch and a real low-contrast mismatch exist in kiosk_standard,
        and this profile has both a hearing and a vision requirement -- both
        barriers, and both existing adaptations, should be produced by the
        unmodified detection/scoring/safety pipeline. No new barrier type or
        adaptation was needed for this profile."""
        session_id, barriers, recommend, apply = self._run_pipeline(self.visual_hearing_support_user.id)

        barrier_types = {b["barrier_type"] for b in barriers["barriers"]}
        self.assertIn("audio_only_alert", barrier_types)
        self.assertIn("low_contrast", barrier_types)

        applied_names = set(apply["applied_adaptations"])
        self.assertIn("caption_audio", applied_names)
        self.assertIn("increase_contrast", applied_names)
        self.assertIn("banner_alert", apply["ui_effects"])
        self.assertIn("contrast", apply["ui_effects"])

    def test_typical_vision_and_hearing_profile_does_not_get_visual_hearing_barriers(self):
        """TEST 5 (Phase 5 section 17): a profile with typical vision AND
        typical hearing must never see either barrier on the same,
        unmodified kiosk_standard environment -- a genuine mismatch check,
        not `if profile == visual_hearing_support`."""
        session_id, barriers, recommend, apply = self._run_pipeline(self.speech_difficulty_user.id)

        barrier_types = {b["barrier_type"] for b in barriers["barriers"]}
        self.assertNotIn("audio_only_alert", barrier_types)
        self.assertNotIn("low_contrast", barrier_types)

    def test_high_interaction_sensitivity_profile_gets_increase_spacing(self):
        session_id, barriers, recommend, apply = self._run_pipeline(self.high_interaction_sensitivity_user.id)

        barrier_types = {b["barrier_type"] for b in barriers["barriers"]}
        self.assertIn("accidental_activation_risk", barrier_types)
        self.assertIn("increase_spacing", apply["applied_adaptations"])
        self.assertEqual(apply["ui_effects"]["spacing_scale"], 1.6)

    def test_typical_interaction_sensitivity_profile_does_not_get_activation_risk_barrier(self):
        """TEST 4 (Phase 6 section 20): a profile that never set
        interaction_sensitivity (defaults to typical) must never see this
        barrier on the same, unmodified kiosk_standard environment."""
        session_id, barriers, recommend, apply = self._run_pipeline(self.low_vision_dexterity_user.id)

        barrier_types = {b["barrier_type"] for b in barriers["barriers"]}
        self.assertNotIn("accidental_activation_risk", barrier_types)
        self.assertNotIn("increase_spacing", apply["applied_adaptations"])

    def test_different_profiles_yield_different_adaptations_same_engine(self):
        _, _, _, apply_a = self._run_pipeline(self.low_vision_dexterity_user.id)
        _, _, _, apply_b = self._run_pipeline(self.cognitive_user.id)

        self.assertNotEqual(set(apply_a["applied_adaptations"]), set(apply_b["applied_adaptations"]))

    def test_baseline_mode_detects_barriers_but_applies_nothing(self):
        session_id, barriers, recommend, apply = self._run_pipeline(
            self.low_vision_dexterity_user.id, baseline_mode=True
        )

        self.assertTrue(len(barriers["barriers"]) > 0)
        self.assertEqual(apply["applied_adaptations"], [])
        self.assertEqual(apply["ui_effects"], {})

    def test_feedback_and_summary_round_trip(self):
        session_id, *_ = self._run_pipeline(self.low_vision_dexterity_user.id)

        feedback_resp = self.client.post(
            f"/api/interactions/{session_id}/feedback/",
            {"completed": True, "errors": 0, "time_seconds": 41, "assistance_requested": False},
            format="json",
        )
        self.assertEqual(feedback_resp.status_code, 200)

        summary = self.client.get(f"/api/interactions/{session_id}/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["status"], "completed")
        self.assertEqual(summary.data["feedback"]["errors"], 0)

    def test_incomplete_feedback_marks_session_abandoned(self):
        session_id, *_ = self._run_pipeline(self.low_vision_dexterity_user.id)

        self.client.post(
            f"/api/interactions/{session_id}/feedback/",
            {"completed": False, "errors": 6, "time_seconds": 90, "assistance_requested": True},
            format="json",
        )
        session = InteractionSession.objects.get(pk=session_id)
        self.assertEqual(session.status, InteractionSession.STATUS_ABANDONED)

    def test_high_risk_adaptation_requires_explicit_confirmation(self):
        adaptation = Adaptation.objects.get(name="alternative_voice_input")
        self.assertTrue(adaptation.requires_confirmation)
        self.assertEqual(adaptation.risk_level, Adaptation.RISK_HIGH)

    def test_analytics_before_after_reports_real_and_seed_data_with_note(self):
        response = self.client.get("/api/analytics/before-after/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("note", response.data)
        self.assertGreaterEqual(response.data["without_abilityos"]["sessions"], 1)
        self.assertGreaterEqual(response.data["with_abilityos"]["sessions"], 1)

    def test_analytics_dashboard_returns_adaptation_usage(self):
        self._run_pipeline(self.low_vision_dexterity_user.id)
        response = self.client.get("/api/analytics/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("adaptations_used", response.data)

    def test_demo_profiles_are_seeded_with_consent_already_granted(self):
        """Phase 2 spec section 11: "All demo profiles must have: consent =
        granted." The Consent screen still runs as a real step in the UI
        journey (pre-checked, and Continue still performs a real POST) —
        this just means a fresh install doesn't start blocked."""

        record = self.client.get(f"/api/users/{self.low_vision_dexterity_user.id}/consent/")
        self.assertEqual(record.status_code, 200)
        self.assertTrue(record.data["granted"])
        self.assertIn("interaction_adaptation", record.data["scope"])

    def test_consent_can_be_revoked_and_regranted(self):
        revoke = self.client.post(
            f"/api/users/{self.low_vision_dexterity_user.id}/consent/", {"granted": False}, format="json"
        )
        self.assertEqual(revoke.status_code, 200)
        self.assertFalse(revoke.data["granted"])

        regrant = self.client.post(
            f"/api/users/{self.low_vision_dexterity_user.id}/consent/",
            {"granted": True, "scope": ["interaction_adaptation"]},
            format="json",
        )
        self.assertEqual(regrant.status_code, 200)
        self.assertTrue(regrant.data["granted"])

    def test_starting_a_session_without_consent_is_rejected(self):
        self.client.post(
            f"/api/users/{self.low_vision_dexterity_user.id}/consent/", {"granted": False}, format="json"
        )
        response = self.client.post(
            "/api/interactions/start/",
            {"user_id": self.low_vision_dexterity_user.id, "task_id": "purchase_ticket"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)

    def test_task_listing_endpoint(self):
        response = self.client.get("/api/tasks/")
        self.assertEqual(response.status_code, 200)
        task_ids = [t["task_id"] for t in response.data]
        self.assertIn("purchase_ticket", task_ids)


class Phase6KioskRenderingContractTests(TestCase):
    """Phase 6 (Adaptive Kiosk Experience) adds no backend endpoints — it
    only renders what Phase 5 already approved. These tests pin down the
    two backend-side guarantees the kiosk UI depends on: applying an
    adaptation only ever changes *presentation* data (never the Task/
    TaskStep facts Phase 3 described), and an adaptation's ui_effects are
    merged into the response as-is, so an unrecognized key can never raise
    a server error — the frontend renderer (KioskView) is solely
    responsible for ignoring keys it doesn't know, and does so (verified
    live via Playwright during Phase 6 sign-off, not re-asserted here)."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.get(username="demo_low_vision_dexterity")

    def _task_snapshot(self):
        task = Task.objects.get(task_id="purchase_ticket")
        steps = list(
            TaskStep.objects.filter(task=task)
            .order_by("order")
            .values("step_id", "name", "description", "required", "controls")
        )
        return {
            "name": task.name,
            "description": task.description,
            "time_limit_seconds": task.time_limit_seconds,
            "steps": steps,
        }

    def test_applying_adaptations_does_not_mutate_task_definition(self):
        before = self._task_snapshot()

        start = self.client.post(
            "/api/interactions/start/",
            {"user_id": self.user.id, "task_id": "purchase_ticket"},
            format="json",
        )
        session_id = start.data["session_id"]
        self.client.post("/api/environment/analyze/", {"session_id": session_id}, format="json")
        self.client.post("/api/barriers/detect/", {"session_id": session_id}, format="json")
        self.client.post("/api/adaptations/recommend/", {"session_id": session_id}, format="json")
        apply = self.client.post(f"/api/interactions/{session_id}/apply/", {}, format="json")

        self.assertTrue(len(apply.data["applied_adaptations"]) > 0)
        self.assertEqual(before, self._task_snapshot())

    def test_apply_marks_the_underlying_adaptation_result_rows_applied(self):
        """The frontend's Developer Panel must show which adaptations are
        live on the kiosk. It derives that from the apply response's
        `applied_adaptations` list rather than the earlier recommend-time
        snapshot (which is never refreshed) — this test pins down that the
        database row apply() flips is the same one `applied_adaptations`
        is built from, so that contract holds."""
        start = self.client.post(
            "/api/interactions/start/",
            {"user_id": self.user.id, "task_id": "purchase_ticket"},
            format="json",
        )
        session_id = start.data["session_id"]
        self.client.post("/api/environment/analyze/", {"session_id": session_id}, format="json")
        self.client.post("/api/barriers/detect/", {"session_id": session_id}, format="json")
        self.client.post("/api/adaptations/recommend/", {"session_id": session_id}, format="json")
        apply = self.client.post(f"/api/interactions/{session_id}/apply/", {}, format="json")

        applied_names = set(apply.data["applied_adaptations"])
        self.assertTrue(applied_names)
        db_applied_names = set(
            AdaptationResult.objects.filter(session_id=session_id, applied=True).values_list(
                "adaptation__name", flat=True
            )
        )
        self.assertEqual(applied_names, db_applied_names)

    def test_apply_merges_an_unrecognized_ui_effect_key_without_error(self):
        """An adaptation's ui_effects dict is merged into the apply response
        verbatim (Phase 5's catalogue, not something Phase 6 revalidates).
        A key the frontend doesn't recognize must not raise a server
        error — it reaches the client, which is responsible for safely
        ignoring it (KioskView only reads a fixed set of known keys)."""
        session = InteractionSession.objects.create(
            user=self.user,
            task=Task.objects.get(task_id="purchase_ticket"),
            status=InteractionSession.STATUS_STARTED,
        )
        barrier = Barrier.objects.create(
            session=session,
            barrier_type=Barrier.TYPE_SMALL_TAP_TARGETS,
            ability_dimension="dexterity",
            severity=0.9,
            confidence=0.95,
            evidence="test fixture",
        )
        odd_adaptation = Adaptation.objects.create(
            name="test_odd_effect_adaptation",
            display_name="Test odd-effect adaptation",
            accessibility_benefit=0.8,
            interaction_cost=0.1,
            risk=0.1,
            risk_level=Adaptation.RISK_LOW,
            allowed_for_tasks=["*"],
            ui_effects={"button_scale": 1.5, "totally_unrecognized_future_key": "some-value"},
        )
        AdaptationResult.objects.create(
            session=session,
            barrier=barrier,
            adaptation=odd_adaptation,
            score=1.0,
            approved=True,
            requires_confirmation=False,
        )

        result = InteractionOrchestrator.apply(session)

        self.assertIn("test_odd_effect_adaptation", result["applied_adaptations"])
        self.assertEqual(result["ui_effects"]["button_scale"], 1.5)
        self.assertEqual(result["ui_effects"]["totally_unrecognized_future_key"], "some-value")


class Phase7FeedbackAnalyticsAndLearningTests(TestCase):
    """Phase 7 — full-stack coverage of the new session lifecycle, event
    tracking, feedback, and analytics endpoints, on top of the real
    session-based pipeline (same one DemoPage/KioskView drives)."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.get(username="demo_low_vision_dexterity")

    def _start_and_apply(self):
        start = self.client.post(
            "/api/interactions/start/", {"user_id": self.user.id, "task_id": "purchase_ticket"}, format="json"
        )
        session_id = start.data["session_id"]
        self.client.post("/api/environment/analyze/", {"session_id": session_id}, format="json")
        self.client.post("/api/barriers/detect/", {"session_id": session_id}, format="json")
        self.client.post("/api/adaptations/recommend/", {"session_id": session_id}, format="json")
        self.client.post(f"/api/interactions/{session_id}/apply/", {}, format="json")
        return session_id

    def test_manual_scenario_one_full_completion_with_feedback(self):
        """Phase 7 section 45: start -> events -> complete -> feedback ->
        verify it surfaces in the session summary and analytics."""
        session_id = self._start_and_apply()

        events_response = self.client.post(
            f"/api/interactions/{session_id}/events/",
            {
                "events": [
                    {"event_type": "control_selected", "step": "select_destination", "control_id": "dest_airport"},
                    {"event_type": "control_selected", "step": "select_ticket_type", "control_id": "ticket_single"},
                ]
            },
            format="json",
        )
        self.assertEqual(events_response.status_code, 201)
        self.assertEqual(events_response.data["recorded"], 2)
        self.assertEqual(events_response.data["status"], "in_progress")

        complete_response = self.client.post(f"/api/interactions/{session_id}/complete/", {}, format="json")
        self.assertEqual(complete_response.status_code, 200)
        self.assertEqual(complete_response.data["status"], "completed")
        self.assertIsNotNone(complete_response.data["completion_time_ms"])

        feedback_response = self.client.post(
            f"/api/interactions/{session_id}/feedback/",
            {"ease_rating": 5, "adaptation_helpfulness": "helped", "assistance_requested": False},
            format="json",
        )
        self.assertEqual(feedback_response.status_code, 200)

        summary = self.client.get(f"/api/interactions/{session_id}/summary/")
        self.assertEqual(summary.data["status"], "completed")
        self.assertEqual(summary.data["feedback"]["ease_rating"], 5)
        self.assertIsNotNone(summary.data["learning_signal"])
        self.assertIsNotNone(summary.data["outcome_score"])

    def test_manual_scenario_two_abandoned_session(self):
        """Phase 7 section 46: start -> back navigation -> abandon ->
        verify status=abandoned and it is not counted as completed."""
        session_id = self._start_and_apply()

        self.client.post(
            f"/api/interactions/{session_id}/events/", {"event_type": "back_navigation", "step": "select_ticket_type"},
            format="json",
        )
        abandon_response = self.client.post(
            f"/api/interactions/{session_id}/abandon/", {"reason": "changed their mind"}, format="json"
        )
        self.assertEqual(abandon_response.status_code, 200)
        self.assertEqual(abandon_response.data["status"], "abandoned")

        summary = self.client.get(f"/api/interactions/{session_id}/summary/")
        self.assertEqual(summary.data["status"], "abandoned")
        self.assertNotEqual(summary.data["status"], "completed")

    def test_manual_scenario_three_assistance_is_reflected_in_analytics(self):
        """Phase 7 section 47: click "Need help?" -> continue -> complete ->
        verify assistance_requested=true, assistance_count>=1."""
        session_id = self._start_and_apply()

        self.client.post(
            f"/api/interactions/{session_id}/events/", {"event_type": "assistance_requested"}, format="json"
        )
        self.client.post(f"/api/interactions/{session_id}/complete/", {}, format="json")
        self.client.post(
            f"/api/interactions/{session_id}/feedback/", {"ease_rating": 3, "assistance_requested": True}, format="json"
        )

        summary = self.client.get(f"/api/interactions/{session_id}/summary/")
        self.assertGreaterEqual(summary.data["assistance_count"], 1)
        self.assertTrue(summary.data["feedback"]["assistance_requested"])

    def test_cannot_complete_an_already_completed_session(self):
        session_id = self._start_and_apply()
        self.client.post(f"/api/interactions/{session_id}/complete/", {}, format="json")
        second = self.client.post(f"/api/interactions/{session_id}/complete/", {}, format="json")
        self.assertEqual(second.status_code, 409)

    def test_invalid_event_type_is_rejected_with_400(self):
        session_id = self._start_and_apply()
        response = self.client.post(
            f"/api/interactions/{session_id}/events/", {"event_type": "not_a_real_event"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_ease_rating_is_rejected_with_400(self):
        session_id = self._start_and_apply()
        response = self.client.post(
            f"/api/interactions/{session_id}/feedback/", {"ease_rating": 99}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_analytics_adaptations_endpoint_reflects_seeded_evidence(self):
        response = self.client.get("/api/analytics/adaptations/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["empty"])
        names = {a["adaptation_id"] for a in response.data["adaptations"]}
        self.assertIn("increase_target_size", names)

    def test_analytics_barriers_endpoint_reflects_seeded_evidence(self):
        response = self.client.get("/api/analytics/barriers/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["empty"])
        types = {b["barrier_type"] for b in response.data["barriers"]}
        self.assertIn("small_tap_targets", types)

    def test_full_regression_still_passes_with_phase7_additions(self):
        """A lightweight canary — the full suite (run separately) is the
        real regression gate, but this confirms the core Phase 1-6 pipeline
        this test class also depends on still works end-to-end."""
        session_id = self._start_and_apply()
        summary = self.client.get(f"/api/interactions/{session_id}/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertTrue(len(summary.data["adaptation_results"]) > 0)


class Phase8OwnershipAndHardeningTests(TestCase):
    """Phase 8 section 8/27: session/feedback ownership is validated, not
    just ability-profile/consent — extending the pre-existing
    `assert_owner` pattern (now centralized in users/services/ownership.py)
    to the Phase 7 endpoints, which didn't have it at all before this
    phase. The anonymous hackathon-demo path (used by every other test in
    this file) must remain completely unaffected."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.get(username="demo_low_vision_dexterity")
        self.other = User.objects.create_user(username="someone_else", password="x")

    def _start_session_as_owner(self):
        start = self.client.post(
            "/api/interactions/start/",
            {"user_id": self.owner.id, "task_id": "purchase_ticket"},
            format="json",
        )
        return start.data["session_id"]

    def test_anonymous_requests_are_unaffected_by_ownership_checks(self):
        """No JWT anywhere in this call — the AllowAny demo path must keep
        working exactly as it did before this phase."""
        session_id = self._start_session_as_owner()
        response = self.client.get(f"/api/interactions/{session_id}/summary/")
        self.assertEqual(response.status_code, 200)

    def test_authenticated_non_owner_cannot_read_another_users_session(self):
        session_id = self._start_session_as_owner()
        self.client.force_authenticate(user=self.other)
        response = self.client.get(f"/api/interactions/{session_id}/summary/")
        self.assertEqual(response.status_code, 403)

    def test_authenticated_non_owner_cannot_submit_feedback_for_another_users_session(self):
        session_id = self._start_session_as_owner()
        self.client.force_authenticate(user=self.other)
        response = self.client.post(
            f"/api/interactions/{session_id}/feedback/", {"completed": True, "ease_rating": 5}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_authenticated_owner_can_still_access_their_own_session(self):
        session_id = self._start_session_as_owner()
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(f"/api/interactions/{session_id}/summary/")
        self.assertEqual(response.status_code, 200)

    def test_authenticated_non_owner_cannot_start_a_session_for_another_user(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.post(
            "/api/interactions/start/", {"user_id": self.owner.id, "task_id": "purchase_ticket"}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_can_access_any_session(self):
        session_id = self._start_session_as_owner()
        staff = User.objects.create_user(username="staffer", password="x", is_staff=True)
        self.client.force_authenticate(user=staff)
        response = self.client.get(f"/api/interactions/{session_id}/summary/")
        self.assertEqual(response.status_code, 200)

    def test_unexpected_server_error_does_not_leak_raw_exception_when_debug_is_off(self):
        from unittest.mock import patch

        session_id = self._start_session_as_owner()
        with patch(
            "api.services.orchestrator.InteractionOrchestrator.summary", side_effect=RuntimeError("db exploded")
        ):
            with self.settings(DEBUG=False):
                response = self.client.get(f"/api/interactions/{session_id}/summary/")
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("db exploded", response.data["detail"])

    def test_unexpected_server_error_includes_detail_when_debug_is_on(self):
        from unittest.mock import patch

        session_id = self._start_session_as_owner()
        with patch(
            "api.services.orchestrator.InteractionOrchestrator.summary", side_effect=RuntimeError("db exploded")
        ):
            with self.settings(DEBUG=True):
                response = self.client.get(f"/api/interactions/{session_id}/summary/")
        self.assertEqual(response.status_code, 500)
        self.assertIn("db exploded", response.data["detail"])
