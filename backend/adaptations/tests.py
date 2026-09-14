import itertools

from django.test import TestCase

from adaptations.models import Adaptation
from adaptations.services.rules import validate_adaptation
from adaptations.services.scoring import rank_candidates_for_barrier
from barriers.models import Barrier
from environments.models import Environment
from feedback.models import InteractionSession
from tasks.models import Task
from users.models import User

_user_counter = itertools.count()


def make_barrier(barrier_type=Barrier.TYPE_SMALL_TAP_TARGETS, severity=0.8, confidence=0.8):
    user = User.objects.create_user(username=f"u_{barrier_type}_{next(_user_counter)}", password="x")
    task, _ = Task.objects.get_or_create(task_id="purchase_ticket", defaults={"name": "Buy a ticket"})
    env, _ = Environment.objects.get_or_create(environment_id="kiosk_standard", defaults={"name": "Kiosk", "data": {}})
    session = InteractionSession.objects.create(user=user, task=task, environment=env)
    return Barrier.objects.create(
        session=session,
        barrier_type=barrier_type,
        ability_dimension="dexterity",
        severity=severity,
        confidence=confidence,
        evidence="test evidence",
    )


class AdaptationScoringTests(TestCase):
    def setUp(self):
        self.cheap_low_risk = Adaptation.objects.create(
            name="increase_target_size",
            display_name="Increase target size",
            resolves_barrier_types=[Barrier.TYPE_SMALL_TAP_TARGETS],
            modality="visual",
            accessibility_benefit=0.9,
            interaction_cost=0.10,
            risk=0.05,
            risk_level=Adaptation.RISK_LOW,
            allowed_for_tasks=["*"],
        )
        self.expensive_high_risk = Adaptation.objects.create(
            name="alternative_voice_input",
            display_name="Alternative voice input",
            resolves_barrier_types=[Barrier.TYPE_SMALL_TAP_TARGETS],
            modality="voice",
            accessibility_benefit=0.8,
            interaction_cost=0.70,
            risk=0.50,
            risk_level=Adaptation.RISK_HIGH,
            requires_confirmation=True,
            allowed_for_tasks=["*"],
        )
        self.disabled = Adaptation.objects.create(
            name="disabled_option",
            display_name="Disabled option",
            resolves_barrier_types=[Barrier.TYPE_SMALL_TAP_TARGETS],
            accessibility_benefit=1.0,
            interaction_cost=0.0,
            risk=0.0,
            enabled=False,
            allowed_for_tasks=["*"],
        )
        self.wrong_task = Adaptation.objects.create(
            name="wrong_task_only",
            display_name="Wrong task only",
            resolves_barrier_types=[Barrier.TYPE_SMALL_TAP_TARGETS],
            accessibility_benefit=1.0,
            interaction_cost=0.0,
            risk=0.0,
            allowed_for_tasks=["some_other_task"],
        )

    def test_low_cost_low_risk_adaptation_outranks_expensive_high_risk_one(self):
        barrier = make_barrier(severity=0.8)

        ranked = rank_candidates_for_barrier(barrier, "purchase_ticket", "visual+haptic")

        names = [c.adaptation.name for c in ranked]
        self.assertIn("increase_target_size", names)
        self.assertLess(names.index("increase_target_size"), names.index("alternative_voice_input"))

    def test_disabled_adaptation_excluded_from_candidates(self):
        barrier = make_barrier()
        ranked = rank_candidates_for_barrier(barrier, "purchase_ticket", "visual")
        names = [c.adaptation.name for c in ranked]
        self.assertNotIn("disabled_option", names)

    def test_task_scoped_adaptation_excluded_for_other_tasks(self):
        barrier = make_barrier()
        ranked = rank_candidates_for_barrier(barrier, "purchase_ticket", "visual")
        names = [c.adaptation.name for c in ranked]
        self.assertNotIn("wrong_task_only", names)

    def test_score_increases_with_barrier_severity(self):
        low_severity_barrier = make_barrier(severity=0.2)
        high_severity_barrier = make_barrier(severity=0.9)

        low_ranked = rank_candidates_for_barrier(low_severity_barrier, "purchase_ticket", "visual")
        high_ranked = rank_candidates_for_barrier(high_severity_barrier, "purchase_ticket", "visual")

        low_score = next(c.score for c in low_ranked if c.adaptation.name == "increase_target_size")
        high_score = next(c.score for c in high_ranked if c.adaptation.name == "increase_target_size")
        self.assertGreater(high_score, low_score)

    def test_preferred_modality_adds_bonus(self):
        barrier = make_barrier()
        visual_ranked = rank_candidates_for_barrier(barrier, "purchase_ticket", "visual")
        voice_ranked = rank_candidates_for_barrier(barrier, "purchase_ticket", "voice")

        visual_bonus = next(c for c in visual_ranked if c.adaptation.name == "increase_target_size")
        self.assertEqual(visual_bonus.user_preference, 0.2)

        no_bonus = next(c for c in voice_ranked if c.adaptation.name == "increase_target_size")
        self.assertEqual(no_bonus.user_preference, 0.0)


class SafetyRuleTests(TestCase):
    def test_high_risk_adaptation_requires_confirmation(self):
        adaptation = Adaptation.objects.create(
            name="risky_one",
            display_name="Risky one",
            resolves_barrier_types=[Barrier.TYPE_SMALL_TAP_TARGETS],
            accessibility_benefit=0.8,
            interaction_cost=0.7,
            risk=0.5,
            risk_level=Adaptation.RISK_HIGH,
            allowed_for_tasks=["*"],
        )
        result = validate_adaptation(adaptation, "purchase_ticket")
        self.assertTrue(result.approved)
        self.assertTrue(result.requires_confirmation)

    def test_low_risk_adaptation_does_not_require_confirmation(self):
        adaptation = Adaptation.objects.create(
            name="safe_one",
            display_name="Safe one",
            resolves_barrier_types=[Barrier.TYPE_SMALL_TAP_TARGETS],
            accessibility_benefit=0.8,
            interaction_cost=0.1,
            risk=0.05,
            risk_level=Adaptation.RISK_LOW,
            allowed_for_tasks=["*"],
        )
        result = validate_adaptation(adaptation, "purchase_ticket")
        self.assertTrue(result.approved)
        self.assertFalse(result.requires_confirmation)

    def test_disabled_adaptation_is_rejected(self):
        adaptation = Adaptation.objects.create(
            name="off_one",
            display_name="Off one",
            resolves_barrier_types=[Barrier.TYPE_SMALL_TAP_TARGETS],
            accessibility_benefit=0.8,
            interaction_cost=0.1,
            risk=0.05,
            enabled=False,
            allowed_for_tasks=["*"],
        )
        result = validate_adaptation(adaptation, "purchase_ticket")
        self.assertFalse(result.approved)

    def test_adaptation_not_allowed_for_task_is_rejected(self):
        adaptation = Adaptation.objects.create(
            name="scoped_one",
            display_name="Scoped one",
            resolves_barrier_types=[Barrier.TYPE_SMALL_TAP_TARGETS],
            accessibility_benefit=0.8,
            interaction_cost=0.1,
            risk=0.05,
            allowed_for_tasks=["other_task"],
        )
        result = validate_adaptation(adaptation, "purchase_ticket")
        self.assertFalse(result.approved)
