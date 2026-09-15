from django.test import TestCase
from rest_framework.test import APIClient

from abilities.models import AbilityProfile, default_dimensions
from adaptations.models import Adaptation, AdaptationResult
from analytics import config, services
from api.services.orchestrator import InteractionOrchestrator
from barriers.models import Barrier
from environments.models import Environment
from feedback.models import Feedback, InteractionSession
from tasks.models import Task
from users.models import User


def _make_user(username):
    return User.objects.create_user(username=username, password="x")


class OutcomeScoreTests(TestCase):
    """Phase 7 section 18/19: deterministic, documented, no AI involved."""

    def setUp(self):
        user = _make_user("scoreuser")
        task = Task.objects.create(task_id="purchase_ticket", name="Buy a ticket")
        self.session = InteractionSession.objects.create(user=user, task=task)

    def test_clean_completion_scores_near_maximum(self):
        feedback = Feedback.objects.create(
            session=self.session, completed=True, errors=0, assistance_requested=False, ease_rating=5
        )
        result = services.calculate_outcome_score(self.session, feedback)
        self.assertGreater(result["score"], 0.9)

    def test_incomplete_with_assistance_scores_low(self):
        self.session.assistance_count = 2
        self.session.save(update_fields=["assistance_count"])
        feedback = Feedback.objects.create(
            session=self.session, completed=False, errors=5, assistance_requested=True, ease_rating=1
        )
        result = services.calculate_outcome_score(self.session, feedback)
        self.assertLess(result["score"], 0.3)

    def test_score_is_bounded_between_zero_and_one(self):
        feedback = Feedback.objects.create(session=self.session, completed=True, errors=0)
        result = services.calculate_outcome_score(self.session, feedback)
        self.assertGreaterEqual(result["score"], 0.0)
        self.assertLessEqual(result["score"], 1.0)

    def test_missing_ease_rating_is_neutral_not_penalizing(self):
        """No rating given must never be silently treated as a bad rating."""
        feedback = Feedback.objects.create(session=self.session, completed=True, errors=0)
        result = services.calculate_outcome_score(self.session, feedback)
        self.assertEqual(result["components"]["ease_improvement"], 0.5)


class LearningSignalTests(TestCase):
    """Phase 7 section 20/50: structured evidence about ONE session, always
    low confidence, never a statistical claim."""

    def setUp(self):
        user = _make_user("signaluser")
        task = Task.objects.create(task_id="purchase_ticket", name="Buy a ticket")
        self.session = InteractionSession.objects.create(user=user, task=task)
        self.barrier = Barrier.objects.create(
            session=self.session,
            barrier_type=Barrier.TYPE_SMALL_TAP_TARGETS,
            ability_dimension="dexterity",
            severity=0.8,
            confidence=0.7,
            evidence="test",
        )
        self.adaptation = Adaptation.objects.create(
            name="increase_target_size",
            display_name="Increase target size",
            accessibility_benefit=0.9,
            interaction_cost=0.1,
            risk=0.05,
            allowed_for_tasks=["*"],
            ui_effects={"button_scale": 1.8},
        )
        self.result = AdaptationResult.objects.create(
            session=self.session, barrier=self.barrier, adaptation=self.adaptation, score=2.5,
            approved=True, applied=True,
        )

    def test_no_signal_without_feedback(self):
        self.assertIsNone(services.generate_learning_signal(self.session, None))

    def test_no_signal_without_an_applied_adaptation(self):
        self.result.applied = False
        self.result.save(update_fields=["applied"])
        feedback = Feedback.objects.create(session=self.session, completed=True)
        self.assertIsNone(services.generate_learning_signal(self.session, feedback))

    def test_successful_independent_completion_is_positive_signal(self):
        feedback = Feedback.objects.create(session=self.session, completed=True, ease_rating=5, assistance_requested=False)
        signal = services.generate_learning_signal(self.session, feedback)
        self.assertEqual(signal["adaptation_id"], "increase_target_size")
        self.assertEqual(signal["barrier_type"], "small_tap_targets")
        self.assertTrue(signal["successful"])
        self.assertTrue(signal["independence_improved"])
        self.assertEqual(signal["confidence"], config.SINGLE_SESSION_CONFIDENCE)

    def test_completion_with_assistance_is_not_independence_improved(self):
        self.session.assistance_count = 1
        self.session.save(update_fields=["assistance_count"])
        feedback = Feedback.objects.create(session=self.session, completed=True, ease_rating=5)
        signal = services.generate_learning_signal(self.session, feedback)
        self.assertTrue(signal["successful"])
        self.assertFalse(signal["independence_improved"])

    def test_failed_task_is_not_successful(self):
        feedback = Feedback.objects.create(session=self.session, completed=False)
        signal = services.generate_learning_signal(self.session, feedback)
        self.assertFalse(signal["successful"])
        self.assertFalse(signal["independence_improved"])


class AdaptationEffectivenessTests(TestCase):
    """Phase 7 section 17/51: transparent states with documented thresholds,
    never a bare AI claim."""

    def setUp(self):
        self.task = Task.objects.create(task_id="purchase_ticket", name="Buy a ticket")
        self.adaptation = Adaptation.objects.create(
            name="increase_target_size", display_name="Increase target size",
            accessibility_benefit=0.9, interaction_cost=0.1, risk=0.05,
            allowed_for_tasks=["*"], ui_effects={"button_scale": 1.8},
        )

    def _applied_session(self, completed, ease_rating, assistance_requested=False, score=2.5):
        user = _make_user(f"user{User.objects.count()}")
        session = InteractionSession.objects.create(user=user, task=self.task)
        barrier = Barrier.objects.create(
            session=session, barrier_type=Barrier.TYPE_SMALL_TAP_TARGETS, ability_dimension="dexterity",
            severity=0.8, confidence=0.7, evidence="test",
        )
        # A varying `score` per session is deliberate here — AdaptationResult
        # orders by `-score` by default, and a fixed score across every test
        # session let a real .distinct()-after-implicit-ordering bug through
        # undetected (fixed in analytics/services.py: distinct() on a
        # values_list() must clear the default ordering first, or SQLite
        # treats each (score, adaptation_id) pair as distinct).
        AdaptationResult.objects.create(
            session=session, barrier=barrier, adaptation=self.adaptation, score=score, approved=True, applied=True,
        )
        Feedback.objects.create(
            session=session, completed=completed, ease_rating=ease_rating, assistance_requested=assistance_requested
        )
        return session

    def test_no_sessions_returns_empty_list(self):
        self.assertEqual(services.adaptation_effectiveness(), [])

    def test_below_minimum_sessions_is_insufficient_data(self):
        self._applied_session(completed=True, ease_rating=5)
        self._applied_session(completed=True, ease_rating=5)
        results = services.adaptation_effectiveness()
        self.assertEqual(results[0]["observed_outcome"], config.INSUFFICIENT_DATA)
        self.assertIsNone(results[0]["confidence"])

    def test_consistently_good_outcomes_are_positive(self):
        for i in range(4):
            self._applied_session(completed=True, ease_rating=5, score=2.0 + i * 0.1)
        results = services.adaptation_effectiveness()
        # Regression guard: the same adaptation applied across sessions with
        # *different* scores must still collapse to exactly one row — a real
        # bug (caught live) previously produced one row per distinct score.
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["sessions"], 4)
        self.assertEqual(results[0]["observed_outcome"], config.POSITIVE_OBSERVED_OUTCOME)
        self.assertIsNotNone(results[0]["confidence"])

    def test_consistently_poor_outcomes_are_negative(self):
        for _ in range(4):
            self._applied_session(completed=False, ease_rating=1, assistance_requested=True)
        results = services.adaptation_effectiveness()
        self.assertEqual(results[0]["observed_outcome"], config.NEGATIVE_OBSERVED_OUTCOME)

    def test_mixed_outcomes_are_inconclusive(self):
        self._applied_session(completed=True, ease_rating=5)
        self._applied_session(completed=False, ease_rating=2, assistance_requested=True)
        self._applied_session(completed=True, ease_rating=3)
        results = services.adaptation_effectiveness()
        self.assertEqual(results[0]["observed_outcome"], config.INCONCLUSIVE)

    def test_unapplied_result_is_excluded(self):
        user = _make_user("unapplied")
        session = InteractionSession.objects.create(user=user, task=self.task)
        barrier = Barrier.objects.create(
            session=session, barrier_type=Barrier.TYPE_SMALL_TAP_TARGETS, ability_dimension="dexterity",
            severity=0.8, confidence=0.7, evidence="test",
        )
        AdaptationResult.objects.create(
            session=session, barrier=barrier, adaptation=self.adaptation, score=2.5, approved=True, applied=False,
        )
        self.assertEqual(services.adaptation_effectiveness(), [])


class BarrierOutcomeTests(TestCase):
    def test_no_barriers_returns_empty_list(self):
        self.assertEqual(services.barrier_outcomes(), [])

    def test_barrier_frequency_and_associated_adaptations(self):
        task = Task.objects.create(task_id="purchase_ticket", name="Buy a ticket")
        adaptation = Adaptation.objects.create(
            name="increase_target_size", display_name="Increase target size",
            accessibility_benefit=0.9, interaction_cost=0.1, risk=0.05,
            allowed_for_tasks=["*"], ui_effects={"button_scale": 1.8},
        )
        for i in range(2):
            user = _make_user(f"barrieruser{i}")
            session = InteractionSession.objects.create(user=user, task=task)
            # Varying severity/score per row guards against the same
            # distinct()-after-implicit-ordering bug analytics/services.py
            # fixed (Barrier orders by `-severity`, AdaptationResult by
            # `-score` by default).
            barrier = Barrier.objects.create(
                session=session, barrier_type=Barrier.TYPE_SMALL_TAP_TARGETS, ability_dimension="dexterity",
                severity=0.8 - i * 0.1, confidence=0.7, evidence="test",
            )
            AdaptationResult.objects.create(
                session=session, barrier=barrier, adaptation=adaptation, score=2.5 + i * 0.1, approved=True, applied=True,
            )

        results = services.barrier_outcomes()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["barrier_type"], "small_tap_targets")
        self.assertEqual(results[0]["frequency"], 2)
        self.assertEqual(results[0]["associated_adaptations"][0]["adaptation__name"], "increase_target_size")


class AnalyticsEndpointTests(TestCase):
    """Empty-state handling (Phase 7 section 39): "no data" must never be
    presented as "measured zero"."""

    def setUp(self):
        self.client = APIClient()

    def test_adaptations_endpoint_reports_empty_when_no_data(self):
        response = self.client.get("/api/analytics/adaptations/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["empty"])
        self.assertEqual(response.data["adaptations"], [])

    def test_barriers_endpoint_reports_empty_when_no_data(self):
        response = self.client.get("/api/analytics/barriers/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["empty"])

    def test_dashboard_reports_empty_when_no_sessions(self):
        response = self.client.get("/api/analytics/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["empty"])
        self.assertNotIn("total_interactions", response.data)

    def test_before_after_never_fabricates_numbers_with_no_sessions(self):
        response = self.client.get("/api/analytics/before-after/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["without_abilityos"]["completion_rate"])
        self.assertEqual(response.data["without_abilityos"]["sessions"], 0)

    def test_sessions_endpoint_reports_empty_when_no_data(self):
        response = self.client.get("/api/analytics/sessions/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["empty"])

    def test_sessions_endpoint_labels_seed_rows(self):
        from adaptations.models import Adaptation
        from api.services.orchestrator import InteractionOrchestrator
        from tasks.models import Task

        user = User.objects.create_user(username="sessionslistuser", password="x")
        task = Task.objects.create(task_id="purchase_ticket", name="Buy a ticket")
        session = InteractionSession.objects.create(user=user, task=task, is_seed=True)
        InteractionOrchestrator.record_feedback(session, {"completed": True, "ease_rating": 4})

        response = self.client.get("/api/analytics/sessions/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["empty"])
        self.assertTrue(response.data["sessions"][0]["is_seed"])
        self.assertEqual(response.data["sessions"][0]["ease_rating"], 4)
