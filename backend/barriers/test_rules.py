"""Phase 4 Barrier Detection Engine tests.

Kept separate from barriers/tests.py (the pre-existing, still-in-use
session-based detector's tests, untouched by this phase) — this file
covers the new barriers/services/{config,result,rules,detector}.py and the
standalone POST /api/barriers/detect/ contract.
"""

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from abilities.models import default_dimensions
from barriers.services.detector import BarrierDetectionService
from barriers.services.rules import (
    AudioOnlyAlertRule,
    LowContrastTextRule,
    SmallTapTargetRule,
    TooManyChoicesRule,
    _contrast_ratio,
)

TASK = {
    "task_id": "purchase_ticket",
    "controls": [
        {"id": "confirm_button", "type": "button"},
        {"id": "other_button", "type": "button"},
    ],
}

SMALL_ENVIRONMENT = {
    "controls": [
        {"id": "confirm_button", "width": 120, "height": 45},
        {"id": "other_button", "width": 200, "height": 60},
    ],
}

ROOMY_ENVIRONMENT = {
    "controls": [
        {"id": "confirm_button", "width": 200, "height": 60},
        {"id": "other_button", "width": 200, "height": 60},
    ],
}


def dims_with(**overrides) -> dict:
    dims = default_dimensions()
    for key, value in overrides.items():
        dims[key] = {"level": value, "confidence": 0.8, "source": "manual"}
    return dims


# --------------------------------------------------------------------------
# Rule 1: small_tap_targets
# --------------------------------------------------------------------------
class SmallTapTargetRuleTests(TestCase):
    def setUp(self):
        self.rule = SmallTapTargetRule()

    def test_reduced_precision_with_small_button_detects_barrier(self):
        results = self.rule.detect(dims_with(dexterity="reduced-precision"), TASK, SMALL_ENVIRONMENT)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].barrier_type, "small_tap_targets")

    def test_single_tap_only_with_small_button_detects_barrier(self):
        results = self.rule.detect(dims_with(dexterity="single-tap-only"), TASK, SMALL_ENVIRONMENT)
        self.assertEqual(len(results), 1)

    def test_typical_dexterity_with_same_button_detects_nothing(self):
        results = self.rule.detect(default_dimensions(), TASK, SMALL_ENVIRONMENT)
        self.assertEqual(results, [])

    def test_button_above_threshold_detects_nothing(self):
        results = self.rule.detect(dims_with(dexterity="reduced-precision"), TASK, ROOMY_ENVIRONMENT)
        self.assertEqual(results, [])

    def test_width_below_threshold_alone_detects_barrier(self):
        env = {"controls": [{"id": "confirm_button", "width": 100, "height": 60}]}
        results = self.rule.detect(dims_with(dexterity="reduced-precision"), TASK, env)
        self.assertEqual(len(results), 1)

    def test_height_below_threshold_alone_detects_barrier(self):
        env = {"controls": [{"id": "confirm_button", "width": 200, "height": 30}]}
        results = self.rule.detect(dims_with(dexterity="reduced-precision"), TASK, env)
        self.assertEqual(len(results), 1)

    def test_severity_is_between_zero_and_one(self):
        results = self.rule.detect(dims_with(dexterity="single-tap-only"), TASK, SMALL_ENVIRONMENT)
        self.assertGreaterEqual(results[0].severity, 0.0)
        self.assertLessEqual(results[0].severity, 1.0)

    def test_evidence_contains_measured_dimensions(self):
        results = self.rule.detect(dims_with(dexterity="reduced-precision"), TASK, SMALL_ENVIRONMENT)
        evidence = results[0].evidence
        self.assertIn("controls", evidence)
        self.assertEqual(evidence["controls"][0]["width"], 120)
        self.assertEqual(evidence["controls"][0]["height"], 45)
        self.assertIn("threshold", evidence)

    def test_never_mentions_an_adaptation(self):
        results = self.rule.detect(dims_with(dexterity="reduced-precision"), TASK, SMALL_ENVIRONMENT)
        payload = str(results[0].as_dict()).lower()
        for forbidden in ("increase", "enlarge", "adaptation", "recommend"):
            self.assertNotIn(forbidden, payload)


# --------------------------------------------------------------------------
# Rule 2: low_contrast_text
# --------------------------------------------------------------------------
class LowContrastTextRuleTests(TestCase):
    def setUp(self):
        self.rule = LowContrastTextRule()
        self.low_contrast_env = {"contrast": {"level": "low", "background": "#ffffff", "foreground": "#999999"}}
        self.high_contrast_env = {"contrast": {"level": "high", "background": "#ffffff", "foreground": "#000000"}}

    def test_low_contrast_sensitive_with_low_contrast_detects_barrier(self):
        results = self.rule.detect(dims_with(vision="low-contrast-sensitive"), TASK, self.low_contrast_env)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].barrier_type, "low_contrast_text")

    def test_typical_vision_with_same_contrast_detects_nothing(self):
        results = self.rule.detect(default_dimensions(), TASK, self.low_contrast_env)
        self.assertEqual(results, [])

    def test_contrast_above_threshold_detects_nothing(self):
        results = self.rule.detect(dims_with(vision="low-contrast-sensitive"), TASK, self.high_contrast_env)
        self.assertEqual(results, [])

    def test_evidence_contains_contrast_information(self):
        results = self.rule.detect(dims_with(vision="low-contrast-sensitive"), TASK, self.low_contrast_env)
        evidence = results[0].evidence
        self.assertIn("contrast_ratio", evidence)
        self.assertIn("threshold", evidence)

    def test_wcag_contrast_ratio_formula_matches_known_value(self):
        # Black-on-white is the maximum possible ratio, exactly 21:1.
        self.assertAlmostEqual(_contrast_ratio("#ffffff", "#000000"), 21.0, places=1)

    def test_falls_back_to_qualitative_level_when_no_colors_given(self):
        results = self.rule.detect(dims_with(vision="low-contrast-sensitive"), TASK, {"contrast": {"level": "low"}})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].evidence["source"], "qualitative_level")


# --------------------------------------------------------------------------
# Rule 3: too_many_choices
# --------------------------------------------------------------------------
class TooManyChoicesRuleTests(TestCase):
    def setUp(self):
        self.rule = TooManyChoicesRule()

    def test_prefers_fewer_choices_with_eight_choices_detects_barrier(self):
        env = {"visible_choice_count": 8}
        results = self.rule.detect(dims_with(cognition="prefers-fewer-choices"), TASK, env)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].barrier_type, "too_many_choices")

    def test_prefers_fewer_choices_with_four_choices_detects_nothing(self):
        env = {"visible_choice_count": 4}
        results = self.rule.detect(dims_with(cognition="prefers-fewer-choices"), TASK, env)
        self.assertEqual(results, [])

    def test_typical_cognition_with_eight_choices_detects_nothing(self):
        env = {"visible_choice_count": 8}
        results = self.rule.detect(default_dimensions(), TASK, env)
        self.assertEqual(results, [])

    def test_evidence_contains_choice_count_and_threshold(self):
        env = {"visible_choice_count": 8}
        results = self.rule.detect(dims_with(cognition="prefers-fewer-choices"), TASK, env)
        evidence = results[0].evidence
        self.assertEqual(evidence["choice_count"], 8)
        self.assertEqual(evidence["threshold"], 4)

    def test_falls_back_to_task_control_count_when_environment_omits_it(self):
        env = {}
        results = self.rule.detect(dims_with(cognition="needs-step-by-step"), TASK, env)
        # TASK has 2 controls, below the threshold of 4 -> no barrier.
        self.assertEqual(results, [])


# --------------------------------------------------------------------------
# Rule 4: audio_only_alert
# --------------------------------------------------------------------------
class AudioOnlyAlertRuleTests(TestCase):
    def setUp(self):
        self.rule = AudioOnlyAlertRule()
        self.audio_only_env = {"alerts": [{"id": "err", "type": "audio", "critical": True, "has_visual_alternative": False}]}
        self.mirrored_env = {"alerts": [{"id": "err", "type": "audio", "critical": True, "has_visual_alternative": True}]}

    def test_partial_hearing_with_critical_audio_only_alert_detects_barrier(self):
        results = self.rule.detect(dims_with(hearing="partial"), TASK, self.audio_only_env)
        self.assertEqual(len(results), 1)

    def test_relies_on_visual_with_critical_audio_only_alert_detects_barrier(self):
        results = self.rule.detect(dims_with(hearing="relies-on-visual"), TASK, self.audio_only_env)
        self.assertEqual(len(results), 1)

    def test_typical_hearing_with_same_alert_detects_nothing(self):
        results = self.rule.detect(default_dimensions(), TASK, self.audio_only_env)
        self.assertEqual(results, [])

    def test_visual_alternative_available_detects_nothing(self):
        results = self.rule.detect(dims_with(hearing="partial"), TASK, self.mirrored_env)
        self.assertEqual(results, [])


# --------------------------------------------------------------------------
# BarrierDetectionService — dedup, sort, no barriers, profile/task dependency
# --------------------------------------------------------------------------
class BarrierDetectionServiceTests(TestCase):
    def test_no_barriers_for_a_fully_typical_profile(self):
        results = BarrierDetectionService.detect(default_dimensions(), TASK, SMALL_ENVIRONMENT)
        self.assertEqual(results, [])

    def test_barriers_sorted_by_severity_descending(self):
        dims = dims_with(dexterity="single-tap-only", cognition="needs-step-by-step")
        env = {**SMALL_ENVIRONMENT, "visible_choice_count": 10}
        results = BarrierDetectionService.detect(dims, TASK, env)
        severities = [r.severity for r in results]
        self.assertEqual(severities, sorted(severities, reverse=True))

    def test_same_environment_different_profile_changes_result(self):
        """The core AbilityOS claim (Phase 4 section 23): the environment
        alone is never the barrier — the mismatch is."""

        typical_result = BarrierDetectionService.detect(default_dimensions(), TASK, SMALL_ENVIRONMENT)
        reduced_precision_result = BarrierDetectionService.detect(
            dims_with(dexterity="reduced-precision"), TASK, SMALL_ENVIRONMENT
        )
        self.assertEqual(typical_result, [])
        self.assertEqual(len(reduced_precision_result), 1)

    def test_result_is_deterministic_across_repeated_calls(self):
        dims = dims_with(dexterity="reduced-precision")
        first = [r.as_dict() for r in BarrierDetectionService.detect(dims, TASK, SMALL_ENVIRONMENT)]
        second = [r.as_dict() for r in BarrierDetectionService.detect(dims, TASK, SMALL_ENVIRONMENT)]
        third = [r.as_dict() for r in BarrierDetectionService.detect(dims, TASK, SMALL_ENVIRONMENT)]
        self.assertEqual(first, second)
        self.assertEqual(second, third)

    def test_no_barrier_result_ever_contains_adaptation_fields(self):
        dims = dims_with(dexterity="single-tap-only", cognition="needs-step-by-step", hearing="relies-on-visual")
        env = {**SMALL_ENVIRONMENT, "visible_choice_count": 10, "alerts": [{"type": "audio", "critical": True}]}
        results = BarrierDetectionService.detect(dims, TASK, env)
        self.assertTrue(len(results) >= 2)
        for r in results:
            payload = r.as_dict()
            for forbidden_key in ("adaptation", "recommended_action", "solution", "fix"):
                self.assertNotIn(forbidden_key, payload)


# --------------------------------------------------------------------------
# Integration: full Phase 2+3+4 pipeline via the real API, using the seeded
# demo data exactly as a judge would see it.
# --------------------------------------------------------------------------
class BarrierDetectionAPIIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()

    def test_low_vision_dexterity_persona_detects_small_tap_targets(self):
        response = self.client.post(
            "/api/barriers/detect/",
            {"user_id": 1, "task_id": "purchase_ticket", "environment_id": "ticket_kiosk_default"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        barrier_types = [b["barrier_type"] for b in response.data["barriers"]]
        self.assertIn("small_tap_targets", barrier_types)

    def test_cognitive_load_persona_detects_too_many_choices(self):
        response = self.client.post(
            "/api/barriers/detect/",
            {"user_id": 3, "task_id": "purchase_ticket", "environment_id": "ticket_kiosk_default"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        barrier_types = [b["barrier_type"] for b in response.data["barriers"]]
        self.assertIn("too_many_choices", barrier_types)

    def test_hearing_difficulty_persona_detects_audio_only_alert(self):
        response = self.client.post(
            "/api/barriers/detect/",
            {"user_id": 2, "task_id": "purchase_ticket", "environment_id": "ticket_kiosk_default"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        barrier_types = [b["barrier_type"] for b in response.data["barriers"]]
        self.assertIn("audio_only_alert", barrier_types)

    def test_unknown_task_returns_404(self):
        response = self.client.post(
            "/api/barriers/detect/",
            {"user_id": 1, "task_id": "does_not_exist", "environment_id": "ticket_kiosk_default"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_unknown_environment_returns_404(self):
        response = self.client.post(
            "/api/barriers/detect/",
            {"user_id": 1, "task_id": "purchase_ticket", "environment_id": "does_not_exist"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_malformed_request_returns_400(self):
        response = self.client.post("/api/barriers/detect/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_response_shape_matches_documented_contract(self):
        response = self.client.post(
            "/api/barriers/detect/",
            {"user_id": 1, "task_id": "purchase_ticket", "environment_id": "ticket_kiosk_default"},
            format="json",
        )
        self.assertEqual(response.data["user_id"], 1)
        self.assertEqual(response.data["task_id"], "purchase_ticket")
        self.assertEqual(response.data["environment_id"], "ticket_kiosk_default")
        barrier = response.data["barriers"][0]
        for field in ("barrier_type", "ability_dimension", "severity", "confidence", "title", "description", "evidence"):
            self.assertIn(field, barrier)

    def test_consent_required_before_barrier_detection(self):
        self.client.post("/api/users/1/consent/", {"granted": False}, format="json")
        response = self.client.post(
            "/api/barriers/detect/",
            {"user_id": 1, "task_id": "purchase_ticket", "environment_id": "ticket_kiosk_default"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_error_response_does_not_leak_stack_trace(self):
        response = self.client.post(
            "/api/barriers/detect/",
            {"user_id": 1, "task_id": "does_not_exist", "environment_id": "ticket_kiosk_default"},
            format="json",
        )
        self.assertNotIn("Traceback", str(response.data))


# --------------------------------------------------------------------------
# Regression: Phase 1/2/3 must still work unchanged.
# --------------------------------------------------------------------------
class RegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_demo")

    def setUp(self):
        self.client = APIClient()

    def test_health_endpoint_still_works(self):
        self.assertEqual(self.client.get("/api/health/").status_code, 200)

    def test_ability_profile_api_still_works(self):
        self.assertEqual(self.client.get("/api/users/1/ability-profile/").status_code, 200)

    def test_consent_api_still_works(self):
        self.assertEqual(self.client.get("/api/users/1/consent/").status_code, 200)

    def test_task_analyze_still_works(self):
        response = self.client.post("/api/tasks/analyze/", {"task_id": "purchase_ticket"}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_environment_analyze_still_works(self):
        response = self.client.post(
            "/api/environment/analyze/", {"environment_id": "ticket_kiosk_default"}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_session_based_barrier_detection_still_works(self):
        """The pre-existing, real-kiosk-powering session flow must be
        completely unaffected by the new standalone mode."""

        start = self.client.post(
            "/api/interactions/start/", {"user_id": 1, "task_id": "purchase_ticket"}, format="json"
        )
        session_id = start.data["session_id"]
        self.client.post("/api/environment/analyze/", {"session_id": session_id}, format="json")
        response = self.client.post("/api/barriers/detect/", {"session_id": session_id}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("barriers", response.data)
