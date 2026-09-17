"""Phase 7 (Advanced Adaptive Intelligence, What-If Simulation & Decision
Support).

Builds on Phase 5/6's already-authenticated, already-owned pipeline. These
tests are specifically about POST /api/what-if/simulate/: override
validation, side-effect freedom, ownership (request.user is always the
profile source, never a client-supplied id), consistency with the
existing standalone barrier/adaptation engine, and AI-ranking safety —
reusing the same mocking pattern adaptations/test_recommender.py already
established for AdaptationRecommender, since What-If calls that exact
function unchanged.
"""

import json
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from abilities.models import AbilityProfile, UserProfileSelection
from abilities.services.profile_service import apply_manual_update, get_or_create_profile
from feedback.models import InteractionSession
from users.models import User
from users.services import consent_service


class WhatIfAuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def test_anonymous_user_cannot_run_a_simulation(self):
        client = APIClient()
        response = client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"dexterity": "typical"}},
            format="json",
        )
        self.assertEqual(response.status_code, 401)


class WhatIfConsentGateTests(TestCase):
    """Held to the same consent rule as the existing standalone
    barrier/adaptation demo endpoints (see WhatIfSimulateView's own
    docstring) — an authenticated user who has never granted consent
    cannot probe What-If either."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def test_authenticated_user_without_consent_cannot_run_a_simulation(self):
        client = APIClient()
        user = User.objects.create_user(username="whatif_no_consent_user", password="x", is_demo_profile=False)
        client.force_authenticate(user=user)
        response = client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"dexterity": "typical"}},
            format="json",
        )
        self.assertEqual(response.status_code, 403)


class WhatIfValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="whatif_validation_user", password="x", is_demo_profile=False)
        consent_service.grant_consent(self.user)
        self.client.force_authenticate(user=self.user)

    def test_missing_task_id_is_rejected(self):
        response = self.client.post(
            "/api/what-if/simulate/", {"overrides": {"dexterity": "typical"}}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_missing_overrides_is_rejected(self):
        response = self.client.post(
            "/api/what-if/simulate/", {"task_id": "purchase_ticket"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_unknown_dimension_is_rejected(self):
        response = self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"eyesight": "typical"}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unknown ability dimension", response.data["detail"])

    def test_invalid_value_for_a_valid_dimension_is_rejected(self):
        response = self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"dexterity": "super-precise"}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid value", response.data["detail"])

    def test_unknown_task_id_is_a_404(self):
        response = self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "not_a_real_task", "overrides": {"dexterity": "typical"}},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_unknown_environment_id_is_a_404(self):
        response = self.client.post(
            "/api/what-if/simulate/",
            {
                "task_id": "purchase_ticket",
                "environment_id": "not_a_real_environment",
                "overrides": {"dexterity": "typical"},
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_valid_dimension_and_value_succeeds(self):
        response = self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"dexterity": "typical"}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)


class WhatIfSimulationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="whatif_sim_user", password="x", is_demo_profile=False)
        profile = get_or_create_profile(self.user)
        apply_manual_update(
            profile,
            dimensions={
                # low-contrast-sensitive, not large-text-needed: the
                # standalone barrier engine's low_contrast rule
                # (barriers/services/config.py::VISION_CONTRAST_TRIGGER_LEVELS)
                # only triggers for this exact vision level -- confirmed by
                # inspecting the actual rule config rather than assumed.
                "vision": {"level": "low-contrast-sensitive", "confidence": 0.85},
                "dexterity": {"level": "reduced-precision", "confidence": 0.8},
            },
        )
        consent_service.grant_consent(self.user)
        self.client.force_authenticate(user=self.user)

    def test_removing_the_triggering_dimension_removes_its_barrier(self):
        response = self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"dexterity": "typical"}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.data

        current_types = {b["barrier_type"] for b in data["current"]["barriers"]}
        simulated_types = {b["barrier_type"] for b in data["simulated"]["barriers"]}

        self.assertIn("small_tap_targets", current_types)
        self.assertNotIn("small_tap_targets", simulated_types)
        # The unrelated vision-driven barrier is unaffected by a
        # dexterity-only override. (This standalone engine's barrier type
        # string is "low_contrast_text" -- distinct from the session-based
        # engine's "low_contrast", a pre-existing naming difference between
        # the two independently-maintained rule sets, not a Phase 7 change.)
        self.assertIn("low_contrast_text", simulated_types)

        self.assertIn("small_tap_targets", data["changes"]["barriers_removed"])
        self.assertEqual(data["changes"]["barriers_added"], [])

    def test_current_state_reflects_the_real_profile_not_the_override(self):
        response = self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"dexterity": "typical"}},
            format="json",
        )
        self.assertEqual(
            response.data["current"]["dimensions"]["dexterity"]["level"], "reduced-precision"
        )
        self.assertEqual(
            response.data["simulated"]["dimensions"]["dexterity"]["level"], "typical"
        )

    def test_overriding_an_unrelated_dimension_does_not_change_the_selected_adaptation(self):
        """Confirms overrides are scoped to exactly the requested
        dimension(s) -- fatigue has no bearing on the vision/dexterity
        barriers this profile already has."""
        response = self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"fatigue": "high"}},
            format="json",
        )
        data = response.data
        current_adaptation = data["current"]["selected_adaptation"]["adaptation_id"]
        simulated_adaptation = data["simulated"]["selected_adaptation"]["adaptation_id"]
        # Both still resolve the same (highest-severity) barrier the same way.
        self.assertEqual(current_adaptation, simulated_adaptation)


class WhatIfSideEffectTests(TestCase):
    """Phase 7 section 17 — the single most important acceptance
    requirement: running a simulation must never mutate real state."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="whatif_sideeffect_user", password="x", is_demo_profile=False)
        profile = get_or_create_profile(self.user)
        apply_manual_update(profile, dimensions={"dexterity": {"level": "reduced-precision", "confidence": 0.8}})
        consent_service.grant_consent(self.user)
        self.client.force_authenticate(user=self.user)

    def test_simulation_does_not_change_the_real_ability_profile(self):
        self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"dexterity": "typical"}},
            format="json",
        )
        profile = AbilityProfile.objects.get(user=self.user)
        self.assertEqual(profile.dimensions["dexterity"]["level"], "reduced-precision")

    def test_simulation_does_not_create_an_interaction_session(self):
        before = InteractionSession.objects.filter(user=self.user).count()
        self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"dexterity": "typical"}},
            format="json",
        )
        after = InteractionSession.objects.filter(user=self.user).count()
        self.assertEqual(before, after)

    def test_simulation_does_not_create_a_profile_selection(self):
        before = UserProfileSelection.objects.filter(user=self.user).count()
        self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"dexterity": "typical"}},
            format="json",
        )
        after = UserProfileSelection.objects.filter(user=self.user).count()
        self.assertEqual(before, after)

    def test_simulation_does_not_change_consent(self):
        self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"dexterity": "typical"}},
            format="json",
        )
        self.assertTrue(consent_service.is_consented_for_adaptation(self.user))

    def test_repeated_simulations_never_accumulate_real_state(self):
        for _ in range(3):
            self.client.post(
                "/api/what-if/simulate/",
                {"task_id": "purchase_ticket", "overrides": {"dexterity": "typical"}},
                format="json",
            )
        self.assertEqual(InteractionSession.objects.filter(user=self.user).count(), 0)
        profile = AbilityProfile.objects.get(user=self.user)
        self.assertEqual(profile.dimensions["dexterity"]["level"], "reduced-precision")


class WhatIfOwnershipTests(TestCase):
    """Phase 7 section 16 — the real AbilityProfile always comes from
    request.user; there is no user_id parameter for a client to supply at
    all, so a User A request can never simulate against User B's profile."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.alice = User.objects.create_user(username="whatif_alice", password="x", is_demo_profile=False)
        self.bob = User.objects.create_user(username="whatif_bob", password="x", is_demo_profile=False)
        apply_manual_update(
            get_or_create_profile(self.alice), dimensions={"vision": {"level": "large-text-needed", "confidence": 0.9}}
        )
        apply_manual_update(
            get_or_create_profile(self.bob), dimensions={"hearing": {"level": "relies-on-visual", "confidence": 0.9}}
        )
        consent_service.grant_consent(self.alice)
        consent_service.grant_consent(self.bob)

    def _simulate_as(self, user):
        self.client.force_authenticate(user=user)
        return self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"fatigue": "moderate"}},
            format="json",
        )

    def test_each_user_only_ever_sees_their_own_profile_in_the_result(self):
        alice_response = self._simulate_as(self.alice)
        bob_response = self._simulate_as(self.bob)

        self.assertEqual(alice_response.data["current"]["dimensions"]["vision"]["level"], "large-text-needed")
        self.assertNotIn("relies-on-visual", json.dumps(alice_response.data["current"]["dimensions"]))

        self.assertEqual(bob_response.data["current"]["dimensions"]["hearing"]["level"], "relies-on-visual")
        self.assertNotIn("large-text-needed", json.dumps(bob_response.data["current"]["dimensions"]))

    def test_there_is_no_request_parameter_that_selects_another_users_profile(self):
        """Even an explicit (bogus, unsupported) user_id in the body is
        simply ignored -- the view never reads one."""
        self.client.force_authenticate(user=self.alice)
        response = self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "user_id": self.bob.id, "overrides": {"fatigue": "moderate"}},
            format="json",
        )
        self.assertEqual(response.data["current"]["dimensions"]["vision"]["level"], "large-text-needed")


class WhatIfConsistencyWithExistingEngineTests(TestCase):
    """Phase 7 sections 8/20 — What-If must use the SAME barrier/adaptation
    engine as the real (non-simulated) standalone endpoints, not a
    reimplementation."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="whatif_consistency_user", password="x", is_demo_profile=False)
        apply_manual_update(
            get_or_create_profile(self.user),
            dimensions={
                "vision": {"level": "large-text-needed", "confidence": 0.85},
                "dexterity": {"level": "reduced-precision", "confidence": 0.8},
            },
        )
        consent_service.grant_consent(self.user)
        self.client.force_authenticate(user=self.user)

    def test_current_state_matches_the_existing_standalone_recommend_endpoint(self):
        what_if_response = self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"fatigue": "moderate"}},
            format="json",
        )
        standalone_response = self.client.post(
            "/api/adaptations/recommend/",
            {"user_id": self.user.id, "task_id": "purchase_ticket", "environment_id": "kiosk_standard"},
            format="json",
        )

        what_if_barrier_types = {b["barrier_type"] for b in what_if_response.data["current"]["barriers"]}
        standalone_barrier_types = {b["barrier_type"] for b in standalone_response.data["barriers"]}
        self.assertEqual(what_if_barrier_types, standalone_barrier_types)

        self.assertEqual(
            what_if_response.data["current"]["selected_adaptation"]["adaptation_id"],
            standalone_response.data["selected_adaptation"]["adaptation_id"],
        )


class WhatIfAIIntegrationTests(TestCase):
    """Phase 7 section 9/23 — What-If delegates to AdaptationRecommender
    unchanged, so it inherits that function's existing AI-safety guarantees
    (already unit-tested directly in adaptations/test_recommender.py).
    These tests only prove the *delegation* itself works end-to-end."""

    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="whatif_ai_user", password="x", is_demo_profile=False)
        apply_manual_update(
            get_or_create_profile(self.user), dimensions={"dexterity": {"level": "reduced-precision", "confidence": 0.8}}
        )
        consent_service.grant_consent(self.user)
        self.client.force_authenticate(user=self.user)

    @patch("adaptations.services.recommender.llm_client.is_configured", return_value=True)
    @patch("adaptations.services.recommender.llm_client.call")
    def test_valid_ai_response_is_reflected_in_the_simulation(self, mock_call, _mock_configured):
        mock_call.return_value = json.dumps(
            {
                "selected_adaptation_id": "increase_target_size",
                "ranked_adaptations": [
                    {"adaptation_id": "increase_target_size", "rank": 1, "rationale": "closest match"}
                ],
                "overall_rationale": "Increasing target size directly addresses the small tap targets.",
            }
        )
        response = self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"fatigue": "moderate"}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        current_selected = response.data["current"]["selected_adaptation"]
        self.assertIsNotNone(current_selected)
        self.assertEqual(current_selected["source"], "ai")

    @patch("adaptations.services.recommender.llm_client.is_configured", return_value=True)
    @patch("adaptations.services.recommender.llm_client.call")
    def test_ai_response_naming_an_adaptation_outside_the_candidate_pool_falls_back_safely(
        self, mock_call, _mock_configured
    ):
        mock_call.return_value = json.dumps(
            {
                "selected_adaptation_id": "totally_made_up_adaptation",
                "ranked_adaptations": [],
                "overall_rationale": "invented",
            }
        )
        response = self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"fatigue": "moderate"}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        current_selected = response.data["current"]["selected_adaptation"]
        if current_selected:
            self.assertEqual(current_selected["source"], "deterministic_fallback")

    @patch("adaptations.services.recommender.llm_client.is_configured", return_value=True)
    @patch("adaptations.services.recommender.llm_client.call")
    def test_malformed_ai_output_falls_back_without_error(self, mock_call, _mock_configured):
        mock_call.return_value = "not valid json"
        response = self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"fatigue": "moderate"}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_ai_unavailable_uses_deterministic_fallback(self):
        # No mocking -- this project's test settings have no AI provider
        # configured, so this exercises the real, unmocked fallback path.
        response = self.client.post(
            "/api/what-if/simulate/",
            {"task_id": "purchase_ticket", "overrides": {"fatigue": "moderate"}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        current_selected = response.data["current"]["selected_adaptation"]
        if current_selected:
            self.assertEqual(current_selected["source"], "deterministic_fallback")
