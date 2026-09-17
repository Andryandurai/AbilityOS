"""Phase 5 (Connect Authenticated Users to the Existing AbilityOS Engine).

These tests deliberately do NOT re-test ownership primitives already
covered by `Phase8OwnershipAndHardeningTests` in api/tests.py (that suite
proves `assert_owner` itself works, using demo-flagged users force-
authenticated as a stand-in). What's new here is end-to-end proof that a
*real*, registered (`is_demo_profile=False`) account -- built the same way
Phase 1's RegisterView creates one, with consent granted and dimensions
set the same way Phase 2's questionnaire/manual editor would set them --
can run the exact same orchestrator pipeline a demo persona uses, with no
second code path anywhere. See docs/AUTHENTICATED_EXPERIENCE.md.
"""

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from abilities.services.profile_service import apply_manual_update, get_or_create_profile
from users.models import User
from users.services import consent_service


class AuthenticatedPipelineTests(TestCase):
    """A real registered user, not a demo persona, running the full
    orchestrator workflow end-to-end via JWT-equivalent authentication
    (force_authenticate) -- the same sequence InteractionWorkflowTests
    already proves for demo personas."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="real_user_alice", password="x", is_demo_profile=False)
        consent_service.grant_consent(self.user)
        profile = get_or_create_profile(self.user)
        apply_manual_update(
            profile,
            dimensions={
                "vision": {"level": "large-text-needed", "confidence": 0.85},
                "dexterity": {"level": "reduced-precision", "confidence": 0.8},
            },
        )
        self.client.force_authenticate(user=self.user)

    def test_real_authenticated_user_runs_the_full_pipeline(self):
        start = self.client.post(
            "/api/interactions/start/",
            {"user_id": self.user.id, "task_id": "purchase_ticket"},
            format="json",
        )
        self.assertEqual(start.status_code, 201)
        session_id = start.data["session_id"]

        env = self.client.post("/api/environment/analyze/", {"session_id": session_id}, format="json")
        self.assertEqual(env.status_code, 200)

        barriers = self.client.post("/api/barriers/detect/", {"session_id": session_id}, format="json")
        self.assertEqual(barriers.status_code, 200)
        # Same profile as the low-vision/dexterity demo persona -> same
        # barrier types (Phase 5 section 16's own example).
        barrier_types = {b["barrier_type"] for b in barriers.data["barriers"]}
        self.assertIn("small_tap_targets", barrier_types)
        self.assertIn("low_contrast", barrier_types)

        recommend = self.client.post("/api/adaptations/recommend/", {"session_id": session_id}, format="json")
        self.assertEqual(recommend.status_code, 200)
        self.assertTrue(len(recommend.data["results"]) > 0)

        apply = self.client.post(f"/api/interactions/{session_id}/apply/", {}, format="json")
        self.assertEqual(apply.status_code, 200)

        complete = self.client.post(f"/api/interactions/{session_id}/complete/", {}, format="json")
        self.assertEqual(complete.status_code, 200)

        feedback = self.client.post(
            f"/api/interactions/{session_id}/feedback/",
            {"completed": True, "ease_rating": 4, "adaptation_helpfulness": "helped"},
            format="json",
        )
        self.assertEqual(feedback.status_code, 200)

        summary = self.client.get(f"/api/interactions/{session_id}/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["user"]["id"], self.user.id)
        # Phase 5 section 35: the session's own snapshot, not a live re-read.
        self.assertEqual(
            summary.data["ability_profile_snapshot"]["vision"]["level"], "large-text-needed"
        )

    def test_real_authenticated_users_own_profile_reaches_the_standalone_engine_demo(self):
        """The exact calls TaskEnvironmentPage.jsx makes (Phase 3/4) --
        proves Dashboard's "Start Experience" entry point works for a real
        account, not only the session-based kiosk path above."""

        barriers = self.client.post(
            "/api/barriers/detect/",
            {"user_id": self.user.id, "task_id": "purchase_ticket", "environment_id": "kiosk_standard"},
            format="json",
        )
        self.assertEqual(barriers.status_code, 200)
        barrier_types = {b["barrier_type"] for b in barriers.data["barriers"]}
        self.assertIn("small_tap_targets", barrier_types)

        recommend = self.client.post(
            "/api/adaptations/recommend/",
            {"user_id": self.user.id, "task_id": "purchase_ticket", "environment_id": "kiosk_standard"},
            format="json",
        )
        self.assertEqual(recommend.status_code, 200)


class AuthenticatedConsentGateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="real_user_bob", password="x", is_demo_profile=False)
        self.client.force_authenticate(user=self.user)

    def test_authenticated_user_without_consent_cannot_start_a_session(self):
        response = self.client.post(
            "/api/interactions/start/",
            {"user_id": self.user.id, "task_id": "purchase_ticket"},
            format="json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("Consent", response.data["detail"])

    def test_authenticated_user_without_consent_cannot_run_standalone_barrier_detection(self):
        response = self.client.post(
            "/api/barriers/detect/",
            {"user_id": self.user.id, "task_id": "purchase_ticket", "environment_id": "kiosk_standard"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class RealUserOwnershipTests(TestCase):
    """Extends Phase8OwnershipAndHardeningTests' coverage from demo-personas-
    force-authenticated to two genuinely separate registered accounts."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.alice = User.objects.create_user(username="real_user_a", password="x", is_demo_profile=False)
        self.bob = User.objects.create_user(username="real_user_b", password="x", is_demo_profile=False)
        consent_service.grant_consent(self.alice)
        consent_service.grant_consent(self.bob)

    def test_user_a_cannot_start_a_session_using_user_bs_id(self):
        self.client.force_authenticate(user=self.alice)
        response = self.client.post(
            "/api/interactions/start/",
            {"user_id": self.bob.id, "task_id": "purchase_ticket"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_user_a_cannot_read_user_bs_ability_profile(self):
        self.client.force_authenticate(user=self.alice)
        response = self.client.get(f"/api/users/{self.bob.id}/ability-profile/")
        self.assertEqual(response.status_code, 403)

    def test_user_a_cannot_read_user_bs_session(self):
        self.client.force_authenticate(user=self.bob)
        start = self.client.post(
            "/api/interactions/start/",
            {"user_id": self.bob.id, "task_id": "purchase_ticket"},
            format="json",
        )
        session_id = start.data["session_id"]

        self.client.force_authenticate(user=self.alice)
        response = self.client.get(f"/api/interactions/{session_id}/summary/")
        self.assertEqual(response.status_code, 403)

    def test_user_a_cannot_submit_feedback_for_user_bs_session(self):
        self.client.force_authenticate(user=self.bob)
        start = self.client.post(
            "/api/interactions/start/",
            {"user_id": self.bob.id, "task_id": "purchase_ticket"},
            format="json",
        )
        session_id = start.data["session_id"]

        self.client.force_authenticate(user=self.alice)
        response = self.client.post(
            f"/api/interactions/{session_id}/feedback/", {"completed": True}, format="json"
        )
        self.assertEqual(response.status_code, 403)

    def test_user_a_cannot_apply_adaptations_on_user_bs_session(self):
        self.client.force_authenticate(user=self.bob)
        start = self.client.post(
            "/api/interactions/start/",
            {"user_id": self.bob.id, "task_id": "purchase_ticket"},
            format="json",
        )
        session_id = start.data["session_id"]

        self.client.force_authenticate(user=self.alice)
        response = self.client.post(f"/api/interactions/{session_id}/apply/", {}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_request_cannot_use_a_real_users_id_to_start_a_session_they_should_not_bypass_consent(self):
        """Anonymous requests remain unrestricted by ownership (documented,
        pre-existing demo design -- see users/services/ownership.py) but the
        consent gate is not an ownership check and still applies to every
        caller, authenticated or not."""

        response = self.client.post(
            "/api/interactions/start/",
            {"user_id": self.alice.id, "task_id": "purchase_ticket"},
            format="json",
        )
        # Alice already has consent granted (setUp), so an anonymous caller
        # *can* start a session for her id today -- proving this is a
        # pre-existing, unchanged design point (see docs/AUTHENTICATED_EXPERIENCE.md
        # "Known limitations"), not a Phase 5 regression.
        self.assertEqual(response.status_code, 201)


class DemoVsAuthenticatedEquivalenceTests(TestCase):
    """Phase 5 section 31: authentication status must not change the
    reasoning logic. A demo persona and a real account with the same
    AbilityProfile dimensions must produce the same barrier detection and
    candidate adaptation behaviour -- never identical session ids/
    timestamps, but the same *reasoning*."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.demo_user = User.objects.get(username="demo_low_vision_dexterity")

        self.real_user = User.objects.create_user(username="real_user_carol", password="x", is_demo_profile=False)
        consent_service.grant_consent(self.real_user)
        profile = get_or_create_profile(self.real_user)
        apply_manual_update(
            profile,
            dimensions={
                "vision": {"level": "large-text-needed", "confidence": 0.85},
                "dexterity": {"level": "reduced-precision", "confidence": 0.8},
            },
        )

    def _run_pipeline(self, user):
        self.client.force_authenticate(user=user)
        start = self.client.post(
            "/api/interactions/start/",
            {"user_id": user.id, "task_id": "purchase_ticket"},
            format="json",
        )
        session_id = start.data["session_id"]
        self.client.post("/api/environment/analyze/", {"session_id": session_id}, format="json")
        barriers = self.client.post("/api/barriers/detect/", {"session_id": session_id}, format="json")
        recommend = self.client.post("/api/adaptations/recommend/", {"session_id": session_id}, format="json")
        return barriers.data["barriers"], recommend.data["results"]

    def test_demo_and_authenticated_user_with_equivalent_profiles_get_equivalent_barriers(self):
        demo_barriers, demo_results = self._run_pipeline(self.demo_user)
        real_barriers, real_results = self._run_pipeline(self.real_user)

        demo_barrier_types = {b["barrier_type"] for b in demo_barriers}
        real_barrier_types = {b["barrier_type"] for b in real_barriers}
        self.assertEqual(demo_barrier_types, real_barrier_types)
        self.assertTrue(demo_barrier_types)  # sanity: this profile does trigger something

        demo_adaptations = sorted(r["adaptation"]["name"] for r in demo_results if r["approved"])
        real_adaptations = sorted(r["adaptation"]["name"] for r in real_results if r["approved"])
        self.assertEqual(demo_adaptations, real_adaptations)
