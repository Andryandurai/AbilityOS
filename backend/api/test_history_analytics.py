"""Phase 6 (Feedback + History + Analytics Integration).

Builds on Phase 5's already-authenticated, already-owned session pipeline
(api/test_authenticated_pipeline.py) -- these tests are specifically about
the NEW history-list endpoint (GET /api/users/{id}/sessions/), the
existing session-detail endpoint reused unmodified for history, and the
one architectural decision this phase made deliberately: the pre-existing
GET /api/analytics/sessions/ (AnalyticsPage.jsx's global demo table) is
NOT filtered by authentication -- see docs/HISTORY_ANALYTICS.md.
"""

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from abilities.services.profile_service import apply_manual_update, get_or_create_profile
from users.models import User
from users.services import consent_service


class UserHistoryListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="history_user", password="x", is_demo_profile=False)
        consent_service.grant_consent(self.user)
        self.client.force_authenticate(user=self.user)

    def _run_full_session(self):
        start = self.client.post(
            "/api/interactions/start/", {"user_id": self.user.id, "task_id": "purchase_ticket"}, format="json"
        )
        session_id = start.data["session_id"]
        self.client.post("/api/environment/analyze/", {"session_id": session_id}, format="json")
        self.client.post("/api/barriers/detect/", {"session_id": session_id}, format="json")
        self.client.post("/api/adaptations/recommend/", {"session_id": session_id}, format="json")
        self.client.post(f"/api/interactions/{session_id}/apply/", {}, format="json")
        self.client.post(f"/api/interactions/{session_id}/complete/", {}, format="json")
        self.client.post(
            f"/api/interactions/{session_id}/feedback/",
            {"completed": True, "ease_rating": 4},
            format="json",
        )
        return session_id

    def test_authenticated_user_with_no_sessions_sees_empty_history(self):
        response = self.client.get(f"/api/users/{self.user.id}/sessions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sessions"], [])

    def test_unauthenticated_request_is_rejected(self):
        anon = APIClient()
        response = anon.get(f"/api/users/{self.user.id}/sessions/")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_sees_own_sessions_newest_first(self):
        profile = get_or_create_profile(self.user)
        apply_manual_update(
            profile,
            dimensions={
                "vision": {"level": "large-text-needed", "confidence": 0.85},
                "dexterity": {"level": "reduced-precision", "confidence": 0.8},
            },
        )
        first_session_id = self._run_full_session()
        second_session_id = self._run_full_session()

        response = self.client.get(f"/api/users/{self.user.id}/sessions/")
        self.assertEqual(response.status_code, 200)
        sessions = response.data["sessions"]
        self.assertEqual(len(sessions), 2)
        # Newest first.
        self.assertEqual(sessions[0]["session_id"], second_session_id)
        self.assertEqual(sessions[1]["session_id"], first_session_id)

        newest = sessions[0]
        self.assertEqual(newest["task_name"], "Buy a ticket")
        self.assertEqual(newest["status"], "completed")
        self.assertTrue(newest["feedback_submitted"])
        self.assertEqual(newest["ease_rating"], 4)
        self.assertGreater(newest["barriers_detected"], 0)
        self.assertGreater(newest["adaptations_applied"], 0)
        self.assertFalse(newest["is_seed"])

    def test_history_reflects_actual_session_count_not_all_sessions_in_db(self):
        """Guards against accidentally reusing an unfiltered queryset."""
        self._run_full_session()
        other_user = User.objects.create_user(username="history_other", password="x", is_demo_profile=False)
        consent_service.grant_consent(other_user)
        other_client = APIClient()
        other_client.force_authenticate(user=other_user)
        other_client.post(
            "/api/interactions/start/", {"user_id": other_user.id, "task_id": "purchase_ticket"}, format="json"
        )

        response = self.client.get(f"/api/users/{self.user.id}/sessions/")
        self.assertEqual(len(response.data["sessions"]), 1)


class HistoryOwnershipTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.alice = User.objects.create_user(username="hist_alice", password="x", is_demo_profile=False)
        self.bob = User.objects.create_user(username="hist_bob", password="x", is_demo_profile=False)
        consent_service.grant_consent(self.alice)
        consent_service.grant_consent(self.bob)

        self.client.force_authenticate(user=self.bob)
        start = self.client.post(
            "/api/interactions/start/", {"user_id": self.bob.id, "task_id": "purchase_ticket"}, format="json"
        )
        self.bob_session_id = start.data["session_id"]
        self.client.post(f"/api/interactions/{self.bob_session_id}/complete/", {}, format="json")

        self.client.force_authenticate(user=self.alice)
        start = self.client.post(
            "/api/interactions/start/", {"user_id": self.alice.id, "task_id": "purchase_ticket"}, format="json"
        )
        self.alice_session_id = start.data["session_id"]

    def test_alice_history_contains_only_her_own_session(self):
        response = self.client.get(f"/api/users/{self.alice.id}/sessions/")
        session_ids = {s["session_id"] for s in response.data["sessions"]}
        self.assertIn(self.alice_session_id, session_ids)
        self.assertNotIn(self.bob_session_id, session_ids)

    def test_bob_history_contains_only_his_own_session(self):
        self.client.force_authenticate(user=self.bob)
        response = self.client.get(f"/api/users/{self.bob.id}/sessions/")
        session_ids = {s["session_id"] for s in response.data["sessions"]}
        self.assertIn(self.bob_session_id, session_ids)
        self.assertNotIn(self.alice_session_id, session_ids)

    def test_alice_cannot_list_bobs_history_via_his_url(self):
        response = self.client.get(f"/api/users/{self.bob.id}/sessions/")
        self.assertEqual(response.status_code, 403)

    def test_query_parameter_cannot_be_used_to_view_another_users_history(self):
        """GET /api/users/{alice}/sessions/?user_id=<bob> while authenticated
        as Alice must still return only Alice's own sessions -- the view
        never reads a user id from the query string at all."""
        response = self.client.get(f"/api/users/{self.alice.id}/sessions/?user_id={self.bob.id}")
        self.assertEqual(response.status_code, 200)
        session_ids = {s["session_id"] for s in response.data["sessions"]}
        self.assertIn(self.alice_session_id, session_ids)
        self.assertNotIn(self.bob_session_id, session_ids)

    def test_alice_cannot_retrieve_bobs_session_detail(self):
        response = self.client.get(f"/api/interactions/{self.bob_session_id}/summary/")
        self.assertEqual(response.status_code, 403)

    def test_alice_cannot_submit_feedback_for_bobs_session(self):
        response = self.client.post(
            f"/api/interactions/{self.bob_session_id}/feedback/", {"completed": True}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_alice_cannot_modify_bobs_session(self):
        response = self.client.post(f"/api/interactions/{self.bob_session_id}/apply/", {}, format="json")
        self.assertEqual(response.status_code, 403)


class ProfileSnapshotHistoryTests(TestCase):
    """Phase 6 section 22/37: a historical session must keep reflecting the
    AbilityProfile as it was at session start, even after the user later
    edits their current profile."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="snapshot_user", password="x", is_demo_profile=False)
        consent_service.grant_consent(self.user)
        profile = get_or_create_profile(self.user)
        apply_manual_update(profile, dimensions={"vision": {"level": "large-text-needed", "confidence": 0.9}})
        self.client.force_authenticate(user=self.user)

        start = self.client.post(
            "/api/interactions/start/", {"user_id": self.user.id, "task_id": "purchase_ticket"}, format="json"
        )
        self.session_id = start.data["session_id"]

    def test_session_summary_keeps_the_original_snapshot_after_profile_changes(self):
        # Edit the CURRENT profile after the session has already started.
        profile = get_or_create_profile(self.user)
        apply_manual_update(profile, dimensions={"vision": {"level": "typical", "confidence": 0.9}})

        summary = self.client.get(f"/api/interactions/{self.session_id}/summary/")
        self.assertEqual(summary.data["ability_profile_snapshot"]["vision"]["level"], "large-text-needed")

        # The live profile really did change -- proving this isn't a no-op.
        live = self.client.get(f"/api/users/{self.user.id}/ability-profile/")
        self.assertEqual(live.data["dimensions"]["vision"]["level"], "typical")


class GlobalAnalyticsRegressionTests(TestCase):
    """Guards the deliberate Phase 6 decision NOT to filter the pre-existing
    GET /api/analytics/sessions/ by authentication -- it must keep serving
    AnalyticsPage.jsx's global demo-wide table exactly as before, for both
    anonymous and authenticated callers."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def test_analytics_sessions_endpoint_stays_global_even_when_authenticated(self):
        client = APIClient()
        someone = User.objects.create_user(username="analytics_regression_user", password="x", is_demo_profile=False)
        client.force_authenticate(user=someone)

        response = client.get("/api/analytics/sessions/")
        self.assertEqual(response.status_code, 200)
        # The seeded demo data includes sessions belonging to the demo
        # personas, none of which is `someone` -- if this endpoint had been
        # accidentally scoped to request.user, this list would be empty.
        self.assertGreater(len(response.data["sessions"]), 0)
        session_user_usernames = set()
        for row in response.data["sessions"]:
            session_user_usernames.add(row.get("task_name"))
        # Sanity: this is genuinely the pre-existing global shape, not a
        # silently-narrowed one.
        self.assertIn("note", response.data)
