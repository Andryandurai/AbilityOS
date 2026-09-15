"""Phase 5 Adaptation Engine + AI Decision Engine + Safety Validation tests.

Kept separate from adaptations/tests.py (the pre-existing, still-in-use
session-based scoring/rules tests, untouched by this phase).
"""

import json
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from abilities.models import default_dimensions
from adaptations.models import Adaptation
from adaptations.services.catalogue import AdaptationCatalogueService
from adaptations.services.recommender import AdaptationRecommender
from adaptations.services.validator import AdaptationSafetyValidator
from ai_engine.services.llm_client import LLMUnavailableError
from barriers.services.result import BarrierResult

TASK = {"task_id": "purchase_ticket", "controls": [{"id": "buy_ticket"}]}
ENVIRONMENT = {}  # unused directly — barriers are injected via mocking BarrierDetectionService in most tests


def dims_with(**overrides) -> dict:
    dims = default_dimensions()
    for key, value in overrides.items():
        dims[key] = {"level": value, "confidence": 0.8, "source": "manual"}
    return dims


def make_barrier(barrier_type="small_tap_targets", ability_dimension="dexterity", severity=0.8, confidence=0.8):
    return BarrierResult(
        barrier_type=barrier_type,
        ability_dimension=ability_dimension,
        severity=severity,
        confidence=confidence,
        title="test barrier",
        description="test barrier description",
        evidence={"ability_value": "reduced-precision"},
    )


# --------------------------------------------------------------------------
# Catalogue
# --------------------------------------------------------------------------
class AdaptationCatalogueTests(TestCase):
    def setUp(self):
        Adaptation.objects.create(
            name="a_enabled",
            display_name="Enabled",
            resolves_barrier_types=["small_tap_targets"],
            accessibility_benefit=0.9,
            interaction_cost=0.1,
            risk=0.05,
            allowed_for_tasks=["*"],
        )
        Adaptation.objects.create(
            name="a_disabled",
            display_name="Disabled",
            resolves_barrier_types=["small_tap_targets"],
            accessibility_benefit=0.9,
            interaction_cost=0.1,
            risk=0.05,
            enabled=False,
            allowed_for_tasks=["*"],
        )
        Adaptation.objects.create(
            name="a_other_barrier",
            display_name="Other barrier",
            resolves_barrier_types=["low_contrast_text"],
            accessibility_benefit=0.9,
            interaction_cost=0.1,
            risk=0.05,
            allowed_for_tasks=["*"],
        )

    def test_catalogue_contains_all_approved_adaptations(self):
        names = {a.name for a in AdaptationCatalogueService.get_all_active()}
        self.assertIn("a_enabled", names)
        self.assertIn("a_other_barrier", names)

    def test_inactive_adaptations_excluded(self):
        names = {a.name for a in AdaptationCatalogueService.get_all_active()}
        self.assertNotIn("a_disabled", names)

    def test_unknown_adaptation_id_returns_none(self):
        self.assertIsNone(AdaptationCatalogueService.get_by_id("does_not_exist"))

    def test_barrier_to_adaptation_mapping_is_correct(self):
        for_small_tap = {a.name for a in AdaptationCatalogueService.get_for_barrier("small_tap_targets")}
        self.assertIn("a_enabled", for_small_tap)
        self.assertNotIn("a_other_barrier", for_small_tap)

    def test_unsupported_barrier_combination_returns_nothing(self):
        result = AdaptationCatalogueService.get_for_barrier("audio_only_alert")
        names = {a.name for a in result}
        self.assertNotIn("a_enabled", names)
        self.assertNotIn("a_other_barrier", names)


# --------------------------------------------------------------------------
# Scoring (reuses adaptations.services.scoring — already tested in
# adaptations/tests.py; these tests confirm compatibility with Phase 4's
# BarrierResult specifically, plus the smallest-intervention property).
# --------------------------------------------------------------------------
class ScoringWithBarrierResultTests(TestCase):
    def setUp(self):
        self.cheap = Adaptation.objects.create(
            name="cheap_fix",
            display_name="Cheap fix",
            resolves_barrier_types=["small_tap_targets"],
            accessibility_benefit=0.9,
            interaction_cost=0.1,
            risk=0.05,
            allowed_for_tasks=["*"],
        )
        self.expensive = Adaptation.objects.create(
            name="expensive_fix",
            display_name="Expensive fix",
            resolves_barrier_types=["small_tap_targets"],
            accessibility_benefit=0.95,
            interaction_cost=0.7,
            risk=0.5,
            allowed_for_tasks=["*"],
        )

    def test_score_is_deterministic(self):
        from adaptations.services.scoring import rank_candidates_for_barrier

        barrier = make_barrier()
        first = rank_candidates_for_barrier(barrier, "purchase_ticket", "visual")
        second = rank_candidates_for_barrier(barrier, "purchase_ticket", "visual")
        self.assertEqual([c.score for c in first], [c.score for c in second])

    def test_smallest_intervention_outranks_more_disruptive_one(self):
        from adaptations.services.scoring import rank_candidates_for_barrier

        barrier = make_barrier()
        ranked = rank_candidates_for_barrier(barrier, "purchase_ticket", "visual")
        names = [c.adaptation.name for c in ranked]
        self.assertLess(names.index("cheap_fix"), names.index("expensive_fix"))

    def test_higher_confidence_barrier_increases_score(self):
        from adaptations.services.scoring import rank_candidates_for_barrier

        low_conf = rank_candidates_for_barrier(make_barrier(confidence=0.2), "purchase_ticket", "visual")
        high_conf = rank_candidates_for_barrier(make_barrier(confidence=0.95), "purchase_ticket", "visual")
        low_score = next(c.score for c in low_conf if c.adaptation.name == "cheap_fix")
        high_score = next(c.score for c in high_conf if c.adaptation.name == "cheap_fix")
        self.assertGreater(high_score, low_score)


# --------------------------------------------------------------------------
# Safety validator
# --------------------------------------------------------------------------
class SafetyValidatorTests(TestCase):
    def setUp(self):
        self.barrier = make_barrier()
        self.profile = dims_with(dexterity="reduced-precision")
        self.task = TASK

    def test_approved_adaptation_passes(self):
        a = Adaptation.objects.create(
            name="ok", display_name="OK", resolves_barrier_types=["small_tap_targets"],
            accessibility_benefit=0.9, interaction_cost=0.1, risk=0.05, allowed_for_tasks=["*"],
        )
        result = AdaptationSafetyValidator.validate(a, self.barrier, self.profile, self.task)
        self.assertTrue(result.approved)

    def test_none_adaptation_fails(self):
        result = AdaptationSafetyValidator.validate(None, self.barrier, self.profile, self.task)
        self.assertFalse(result.approved)

    def test_inactive_adaptation_fails(self):
        a = Adaptation.objects.create(
            name="off", display_name="Off", resolves_barrier_types=["small_tap_targets"],
            accessibility_benefit=0.9, interaction_cost=0.1, risk=0.05, enabled=False, allowed_for_tasks=["*"],
        )
        result = AdaptationSafetyValidator.validate(a, self.barrier, self.profile, self.task)
        self.assertFalse(result.approved)

    def test_wrong_barrier_fails(self):
        a = Adaptation.objects.create(
            name="wrong_barrier", display_name="Wrong", resolves_barrier_types=["low_contrast_text"],
            accessibility_benefit=0.9, interaction_cost=0.1, risk=0.05, allowed_for_tasks=["*"],
        )
        result = AdaptationSafetyValidator.validate(a, self.barrier, self.profile, self.task)
        self.assertFalse(result.approved)

    def test_missing_ability_dimension_fails(self):
        a = Adaptation.objects.create(
            name="dim_check", display_name="Dim check", resolves_barrier_types=["small_tap_targets"],
            accessibility_benefit=0.9, interaction_cost=0.1, risk=0.05, allowed_for_tasks=["*"],
        )
        result = AdaptationSafetyValidator.validate(a, self.barrier, {}, self.task)
        self.assertFalse(result.approved)

    def test_task_incompatible_adaptation_fails(self):
        a = Adaptation.objects.create(
            name="scoped", display_name="Scoped", resolves_barrier_types=["small_tap_targets"],
            accessibility_benefit=0.9, interaction_cost=0.1, risk=0.05, allowed_for_tasks=["other_task"],
        )
        result = AdaptationSafetyValidator.validate(a, self.barrier, self.profile, self.task)
        self.assertFalse(result.approved)

    def test_unsupported_ui_effect_key_fails(self):
        a = Adaptation.objects.create(
            name="unsafe_effect", display_name="Unsafe", resolves_barrier_types=["small_tap_targets"],
            accessibility_benefit=0.9, interaction_cost=0.1, risk=0.05, allowed_for_tasks=["*"],
            ui_effects={"inject_script": "alert(1)"},
        )
        result = AdaptationSafetyValidator.validate(a, self.barrier, self.profile, self.task)
        self.assertFalse(result.approved)

    def test_high_risk_requires_confirmation(self):
        a = Adaptation.objects.create(
            name="risky", display_name="Risky", resolves_barrier_types=["small_tap_targets"],
            accessibility_benefit=0.9, interaction_cost=0.7, risk=0.5,
            risk_level=Adaptation.RISK_HIGH, allowed_for_tasks=["*"],
        )
        result = AdaptationSafetyValidator.validate(a, self.barrier, self.profile, self.task)
        self.assertTrue(result.approved)
        self.assertTrue(result.requires_confirmation)


# --------------------------------------------------------------------------
# Recommender: no-barrier / no-candidate / fallback paths
# --------------------------------------------------------------------------
class RecommenderUnitTests(TestCase):
    def test_no_barriers_returns_null_selection_without_ai_call(self):
        with patch("barriers.services.detector.BarrierDetectionService.detect", return_value=[]):
            with patch("ai_engine.services.llm_client.call") as mock_call:
                result = AdaptationRecommender.recommend(default_dimensions(), TASK, {}, "visual")
        mock_call.assert_not_called()
        self.assertEqual(result["barriers"], [])
        self.assertIsNone(result["selected_adaptation"])
        self.assertEqual(result["reason"], "No accessibility mismatch detected.")

    def test_no_candidates_for_detected_barrier_returns_null_selection(self):
        Adaptation.objects.all().delete()
        with patch("barriers.services.detector.BarrierDetectionService.detect", return_value=[make_barrier()]):
            result = AdaptationRecommender.recommend(dims_with(dexterity="reduced-precision"), TASK, {}, "visual")
        self.assertIsNone(result["selected_adaptation"])
        self.assertIn("No approved adaptation", result["reason"])


# --------------------------------------------------------------------------
# AI Decision Engine (mocked LLM — never depends on a real external API)
# --------------------------------------------------------------------------
class AIRecommenderTests(TestCase):
    def setUp(self):
        Adaptation.objects.create(
            name="increase_target_size", display_name="Increase target size",
            resolves_barrier_types=["small_tap_targets"], accessibility_benefit=0.9,
            interaction_cost=0.1, risk=0.05, allowed_for_tasks=["*"],
        )
        Adaptation.objects.create(
            name="alternative_voice_input", display_name="Alternative voice input",
            resolves_barrier_types=["small_tap_targets"], accessibility_benefit=0.8,
            interaction_cost=0.7, risk=0.5, risk_level=Adaptation.RISK_HIGH,
            requires_confirmation=True, allowed_for_tasks=["*"],
        )
        self.barrier = make_barrier()
        self.profile = dims_with(dexterity="reduced-precision")

    def _recommend(self):
        with patch("barriers.services.detector.BarrierDetectionService.detect", return_value=[self.barrier]):
            return AdaptationRecommender.recommend(self.profile, TASK, {}, "visual")

    @patch("adaptations.services.recommender.llm_client.is_configured", return_value=True)
    @patch("adaptations.services.recommender.llm_client.call")
    def test_valid_ai_response_is_accepted(self, mock_call, _mock_configured):
        mock_call.return_value = json.dumps(
            {
                "selected_adaptation_id": "increase_target_size",
                "ranked_adaptations": [
                    {"adaptation_id": "increase_target_size", "rank": 1, "rationale": "Smallest fix."}
                ],
                "overall_rationale": "Directly resolves the barrier with minimal change.",
            }
        )
        result = self._recommend()
        self.assertEqual(result["selected_adaptation"]["adaptation_id"], "increase_target_size")
        self.assertEqual(result["selected_adaptation"]["source"], "ai")

    @patch("adaptations.services.recommender.llm_client.is_configured", return_value=True)
    @patch("adaptations.services.recommender.llm_client.call")
    def test_unknown_adaptation_id_is_rejected(self, mock_call, _mock_configured):
        mock_call.return_value = json.dumps(
            {
                "selected_adaptation_id": "some_new_adaptation_the_ai_made_up",
                "ranked_adaptations": [],
                "overall_rationale": "hallucinated",
            }
        )
        result = self._recommend()
        self.assertEqual(result["selected_adaptation"]["source"], "deterministic_fallback")

    @patch("adaptations.services.recommender.llm_client.is_configured", return_value=True)
    @patch("adaptations.services.recommender.llm_client.call")
    def test_invalid_json_is_handled(self, mock_call, _mock_configured):
        mock_call.return_value = "not valid json {{{"
        result = self._recommend()
        self.assertEqual(result["selected_adaptation"]["source"], "deterministic_fallback")

    @patch("adaptations.services.recommender.llm_client.is_configured", return_value=True)
    @patch("adaptations.services.recommender.llm_client.call")
    def test_missing_required_field_is_handled(self, mock_call, _mock_configured):
        mock_call.return_value = json.dumps({"ranked_adaptations": []})  # missing selected_adaptation_id
        result = self._recommend()
        self.assertEqual(result["selected_adaptation"]["source"], "deterministic_fallback")

    @patch("adaptations.services.recommender.llm_client.is_configured", return_value=True)
    @patch("adaptations.services.recommender.llm_client.call")
    def test_ranking_referencing_unknown_adaptation_is_rejected(self, mock_call, _mock_configured):
        mock_call.return_value = json.dumps(
            {
                "selected_adaptation_id": "increase_target_size",
                "ranked_adaptations": [
                    {"adaptation_id": "increase_target_size", "rank": 1, "rationale": "ok"},
                    {"adaptation_id": "made_up_adaptation", "rank": 2, "rationale": "hallucinated"},
                ],
                "overall_rationale": "x",
            }
        )
        result = self._recommend()
        self.assertEqual(result["selected_adaptation"]["source"], "deterministic_fallback")

    @patch("adaptations.services.recommender.llm_client.is_configured", return_value=True)
    @patch("adaptations.services.recommender.llm_client.call")
    def test_llm_timeout_triggers_fallback(self, mock_call, _mock_configured):
        mock_call.side_effect = LLMUnavailableError("timeout")
        result = self._recommend()
        self.assertEqual(result["selected_adaptation"]["source"], "deterministic_fallback")

    def test_no_api_key_triggers_fallback_without_calling_llm(self):
        with patch("adaptations.services.recommender.llm_client.call") as mock_call:
            result = self._recommend()  # default settings: AI_AVAILABLE=False
        mock_call.assert_not_called()
        self.assertEqual(result["selected_adaptation"]["source"], "deterministic_fallback")

    @patch("adaptations.services.recommender.llm_client.is_configured", return_value=True)
    @patch("adaptations.services.recommender.llm_client.call")
    def test_result_never_contains_an_invented_adaptation(self, mock_call, _mock_configured):
        """Whatever the LLM says, the final selected_adaptation_id must
        always be a real catalogue entry (Phase 5 sections 22/42)."""

        mock_call.return_value = json.dumps(
            {"selected_adaptation_id": "completely_fabricated", "ranked_adaptations": [], "overall_rationale": "x"}
        )
        result = self._recommend()
        real_ids = {"increase_target_size", "alternative_voice_input"}
        self.assertIn(result["selected_adaptation"]["adaptation_id"], real_ids)


# --------------------------------------------------------------------------
# End-to-end: the three demo personas, via the real API, using seeded data.
# --------------------------------------------------------------------------
class RecommendationAPIIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()

    def _recommend(self, user_id):
        return self.client.post(
            "/api/adaptations/recommend/",
            {"user_id": user_id, "task_id": "purchase_ticket", "environment_id": "ticket_kiosk_default"},
            format="json",
        )

    def test_low_vision_dexterity_persona_selects_increase_target_size(self):
        response = self._recommend(1)
        self.assertEqual(response.status_code, 200)
        candidate_ids = [c["adaptation_id"] for c in response.data["candidates"]]
        self.assertIn("increase_target_size", candidate_ids)
        self.assertIn("increase_spacing", candidate_ids)
        self.assertEqual(response.data["selected_adaptation"]["adaptation_id"], "increase_target_size")
        self.assertTrue(response.data["selected_adaptation"]["validated"])

    def test_hearing_difficulty_persona_selects_caption_or_haptic(self):
        response = self._recommend(2)
        self.assertEqual(response.status_code, 200)
        candidate_ids = [c["adaptation_id"] for c in response.data["candidates"]]
        self.assertIn("caption_audio", candidate_ids)
        self.assertIn("haptic_confirmation", candidate_ids)
        self.assertIn(response.data["selected_adaptation"]["adaptation_id"], {"caption_audio", "haptic_confirmation"})

    def test_cognitive_load_persona_selects_a_choice_reduction_adaptation(self):
        response = self._recommend(3)
        self.assertEqual(response.status_code, 200)
        candidate_ids = [c["adaptation_id"] for c in response.data["candidates"]]
        self.assertIn("step_by_step_flow", candidate_ids)
        self.assertIn(
            response.data["selected_adaptation"]["adaptation_id"],
            {"step_by_step_flow", "reduce_choice_count", "simplify_navigation"},
        )

    def test_consent_required_before_recommendation(self):
        self.client.post("/api/users/1/consent/", {"granted": False}, format="json")
        response = self._recommend(1)
        self.assertEqual(response.status_code, 403)

    def test_unknown_task_returns_404(self):
        response = self.client.post(
            "/api/adaptations/recommend/",
            {"user_id": 1, "task_id": "does_not_exist", "environment_id": "ticket_kiosk_default"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_malformed_request_returns_400(self):
        response = self.client.post("/api/adaptations/recommend/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_response_never_leaks_stack_trace(self):
        response = self.client.post(
            "/api/adaptations/recommend/",
            {"user_id": 1, "task_id": "does_not_exist", "environment_id": "ticket_kiosk_default"},
            format="json",
        )
        self.assertNotIn("Traceback", str(response.data))


# --------------------------------------------------------------------------
# Regression: Phase 1-4 must still work unchanged.
# --------------------------------------------------------------------------
class RegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()

    def test_health_still_works(self):
        self.assertEqual(self.client.get("/api/health/").status_code, 200)

    def test_task_analyze_still_works(self):
        self.assertEqual(
            self.client.post("/api/tasks/analyze/", {"task_id": "purchase_ticket"}, format="json").status_code, 200
        )

    def test_standalone_barrier_detection_still_works(self):
        response = self.client.post(
            "/api/barriers/detect/",
            {"user_id": 1, "task_id": "purchase_ticket", "environment_id": "ticket_kiosk_default"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_session_based_recommendation_still_works(self):
        """The pre-existing, real-kiosk-powering session flow — including
        the smallest-intervention outcome it's always produced — must be
        completely unaffected by the new standalone mode."""

        start = self.client.post(
            "/api/interactions/start/", {"user_id": 1, "task_id": "purchase_ticket"}, format="json"
        )
        session_id = start.data["session_id"]
        self.client.post("/api/environment/analyze/", {"session_id": session_id}, format="json")
        self.client.post("/api/barriers/detect/", {"session_id": session_id}, format="json")
        response = self.client.post("/api/adaptations/recommend/", {"session_id": session_id}, format="json")
        self.assertEqual(response.status_code, 200)
        adaptation_names = [r["adaptation"]["name"] for r in response.data["results"]]
        self.assertIn("increase_target_size", adaptation_names)
