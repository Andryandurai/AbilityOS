from django.test import TestCase

from abilities.models import AbilityProfile, default_dimensions
from api.services.orchestrator import InteractionOrchestrator
from barriers.models import Barrier
from environments.models import Environment
from feedback.models import Feedback, InteractionSession
from tasks.models import Task
from users.models import User


class FeedbackModelTests(TestCase):
    def test_feedback_defaults(self):
        user = User.objects.create_user(username="fbuser", password="x")
        task = Task.objects.create(task_id="purchase_ticket", name="Buy a ticket")
        session = InteractionSession.objects.create(user=user, task=task)

        feedback = Feedback.objects.create(session=session, completed=True, time_seconds=30)

        self.assertEqual(feedback.errors, 0)
        self.assertFalse(feedback.assistance_requested)
        self.assertEqual(feedback.effort, 3)


class LearningLoopTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="learner", password="x")
        dims = default_dimensions()
        dims["dexterity"] = {"level": "reduced-precision", "confidence": 0.5, "source": "manual"}
        self.profile = AbilityProfile.objects.create(user=self.user, dimensions=dims)
        self.task = Task.objects.create(task_id="purchase_ticket", name="Buy a ticket")
        self.environment = Environment.objects.create(environment_id="kiosk_standard", name="Kiosk", data={})
        self.session = InteractionSession.objects.create(user=self.user, task=self.task, environment=self.environment)
        self.barrier = Barrier.objects.create(
            session=self.session,
            barrier_type=Barrier.TYPE_SMALL_TAP_TARGETS,
            ability_dimension="dexterity",
            severity=0.8,
            confidence=0.5,
            evidence="test",
        )

    def test_clean_completion_increases_confidence(self):
        InteractionOrchestrator.record_feedback(
            self.session, {"completed": True, "errors": 0, "time_seconds": 30}
        )
        self.profile.refresh_from_db()
        self.assertGreater(self.profile.dimensions["dexterity"]["confidence"], 0.5)

    def test_poor_outcome_decreases_confidence(self):
        InteractionOrchestrator.record_feedback(
            self.session, {"completed": False, "errors": 5, "time_seconds": 90}
        )
        self.profile.refresh_from_db()
        self.assertLess(self.profile.dimensions["dexterity"]["confidence"], 0.5)

    def test_session_status_reflects_completion(self):
        InteractionOrchestrator.record_feedback(self.session, {"completed": True, "time_seconds": 20})
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, InteractionSession.STATUS_COMPLETED)
