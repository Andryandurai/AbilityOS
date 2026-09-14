from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from adaptations.models import Adaptation
from feedback.models import InteractionSession
from users.models import User


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

    def test_consent_starts_ungranted_and_must_be_explicitly_agreed(self):
        record = self.client.get(f"/api/users/{self.low_vision_dexterity_user.id}/consent/")
        self.assertEqual(record.status_code, 200)
        self.assertFalse(record.data["granted"])

        agree = self.client.post(
            f"/api/users/{self.low_vision_dexterity_user.id}/consent/",
            {"granted": True, "scope": ["interaction_adaptation"]},
            format="json",
        )
        self.assertEqual(agree.status_code, 200)
        self.assertTrue(agree.data["granted"])

    def test_task_listing_endpoint(self):
        response = self.client.get("/api/tasks/")
        self.assertEqual(response.status_code, 200)
        task_ids = [t["task_id"] for t in response.data]
        self.assertIn("purchase_ticket", task_ids)
