import json
from unittest.mock import patch

from django.test import TestCase, override_settings

from adaptations.models import Adaptation
from ai_engine.services.decision_engine import decide
from ai_engine.services.schemas import AIDecisionResponse, ValidationError
from barriers.models import Barrier
from environments.models import Environment
from feedback.models import InteractionSession
from tasks.models import Task, TaskStep
from users.models import User


class AIDecisionSchemaTests(TestCase):
    def test_valid_payload_parses(self):
        payload = {
            "decisions": [
                {
                    "barrier_type": "small_tap_targets",
                    "selected_adaptation": "increase_target_size",
                    "confidence": 0.9,
                    "rationale": "Direct fix, low cost.",
                }
            ]
        }
        parsed = AIDecisionResponse.model_validate(payload)
        self.assertEqual(len(parsed.decisions), 1)
        self.assertEqual(parsed.decisions[0].selected_adaptation, "increase_target_size")

    def test_confidence_out_of_range_is_rejected(self):
        payload = {
            "decisions": [
                {
                    "barrier_type": "small_tap_targets",
                    "selected_adaptation": "increase_target_size",
                    "confidence": 1.7,
                    "rationale": "invalid confidence",
                }
            ]
        }
        with self.assertRaises(ValidationError):
            AIDecisionResponse.model_validate(payload)

    def test_missing_field_is_rejected(self):
        payload = {"decisions": [{"barrier_type": "small_tap_targets"}]}
        with self.assertRaises(ValidationError):
            AIDecisionResponse.model_validate(payload)


class DecisionEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="x")
        self.task = Task.objects.create(task_id="purchase_ticket", name="Buy a ticket")
        TaskStep.objects.create(task=self.task, order=1, step_id="confirm_purchase", name="Confirm")
        self.environment = Environment.objects.create(environment_id="kiosk_standard", name="Kiosk", data={})
        self.session = InteractionSession.objects.create(user=self.user, task=self.task, environment=self.environment)

        self.good_adaptation = Adaptation.objects.create(
            name="increase_target_size",
            display_name="Increase target size",
            resolves_barrier_types=[Barrier.TYPE_SMALL_TAP_TARGETS],
            accessibility_benefit=0.9,
            interaction_cost=0.1,
            risk=0.05,
            allowed_for_tasks=["*"],
        )
        self.other_adaptation = Adaptation.objects.create(
            name="alternative_voice_input",
            display_name="Alternative voice input",
            resolves_barrier_types=[Barrier.TYPE_SMALL_TAP_TARGETS],
            accessibility_benefit=0.8,
            interaction_cost=0.7,
            risk=0.5,
            risk_level=Adaptation.RISK_HIGH,
            allowed_for_tasks=["*"],
        )

        from abilities.models import AbilityProfile, default_dimensions

        dims = default_dimensions()
        dims["dexterity"] = {"level": "reduced-precision", "confidence": 0.8, "source": "manual"}
        self.profile = AbilityProfile.objects.create(user=self.user, dimensions=dims)

        self.barrier = Barrier.objects.create(
            session=self.session,
            barrier_type=Barrier.TYPE_SMALL_TAP_TARGETS,
            ability_dimension="dexterity",
            severity=0.8,
            confidence=0.8,
            evidence="test",
        )

    @override_settings(AI_AVAILABLE=False)
    def test_falls_back_when_ai_not_configured(self):
        outcome = decide([self.barrier], self.task, self.profile)
        self.assertFalse(outcome.ai_used)
        self.assertEqual(len(outcome.decisions), 1)
        self.assertEqual(outcome.decisions[0].source, "fallback")
        self.assertEqual(outcome.decisions[0].adaptation.name, "increase_target_size")

    @override_settings(AI_AVAILABLE=True, AI_PROVIDER="openai")
    @patch("ai_engine.services.llm_client.call")
    def test_uses_ai_choice_when_valid(self, mock_call):
        mock_call.return_value = json.dumps(
            {
                "decisions": [
                    {
                        "barrier_type": "small_tap_targets",
                        "selected_adaptation": "increase_target_size",
                        "confidence": 0.95,
                        "rationale": "Smallest effective change.",
                    }
                ]
            }
        )
        outcome = decide([self.barrier], self.task, self.profile)
        self.assertTrue(outcome.ai_used)
        self.assertEqual(outcome.decisions[0].source, "ai")
        self.assertEqual(outcome.decisions[0].adaptation.name, "increase_target_size")

    @override_settings(AI_AVAILABLE=True, AI_PROVIDER="openai")
    @patch("ai_engine.services.llm_client.call")
    def test_falls_back_when_ai_picks_adaptation_outside_candidates(self, mock_call):
        mock_call.return_value = json.dumps(
            {
                "decisions": [
                    {
                        "barrier_type": "small_tap_targets",
                        "selected_adaptation": "an_adaptation_that_does_not_exist",
                        "confidence": 0.95,
                        "rationale": "hallucinated",
                    }
                ]
            }
        )
        outcome = decide([self.barrier], self.task, self.profile)
        self.assertEqual(outcome.decisions[0].source, "fallback")
        self.assertEqual(outcome.decisions[0].adaptation.name, "increase_target_size")

    @override_settings(AI_AVAILABLE=True, AI_PROVIDER="openai")
    @patch("ai_engine.services.llm_client.call")
    def test_falls_back_on_malformed_json(self, mock_call):
        mock_call.return_value = "not valid json {{{"
        outcome = decide([self.barrier], self.task, self.profile)
        self.assertFalse(outcome.ai_used)
        self.assertIsNotNone(outcome.ai_error)
        self.assertEqual(outcome.decisions[0].source, "fallback")

    @override_settings(AI_AVAILABLE=True, AI_PROVIDER="openai")
    @patch("ai_engine.services.llm_client.call")
    def test_falls_back_when_llm_raises(self, mock_call):
        from ai_engine.services.llm_client import LLMUnavailableError

        mock_call.side_effect = LLMUnavailableError("network timeout")
        outcome = decide([self.barrier], self.task, self.profile)
        self.assertFalse(outcome.ai_used)
        self.assertIn("timeout", outcome.ai_error)
        self.assertEqual(outcome.decisions[0].source, "fallback")

    def test_no_candidates_returns_empty_decisions(self):
        Adaptation.objects.all().delete()
        outcome = decide([self.barrier], self.task, self.profile)
        self.assertEqual(outcome.decisions, [])
