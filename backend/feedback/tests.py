from django.test import TestCase

from abilities.models import AbilityProfile, default_dimensions
from api.services.orchestrator import InteractionOrchestrator, OrchestratorError
from barriers.models import Barrier
from environments.models import Environment
from feedback.models import Feedback, InteractionEvent, InteractionSession
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
    """Phase 7 section 21 ("VERY IMPORTANT: do NOT auto-change the user
    profile based on one session") retired the earlier pass's automatic
    confidence nudge — tracing it through, that stored confidence value fed
    straight into Phase 5's scoring formula on the next session, so it was
    silently influencing future recommendations too (section 22). These
    tests now guard the corrected behaviour: feedback still drives the
    session's status, but never touches the Ability Profile. See
    docs/PHASE_7.md "Learning Signal" for the replacement (an on-demand,
    non-mutating structured signal) and analytics/services.py for where it
    now lives instead."""

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

    def test_clean_completion_does_not_change_profile_confidence(self):
        InteractionOrchestrator.record_feedback(
            self.session, {"completed": True, "errors": 0, "time_seconds": 30}
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.dimensions["dexterity"]["confidence"], 0.5)

    def test_poor_outcome_does_not_change_profile_confidence(self):
        InteractionOrchestrator.record_feedback(
            self.session, {"completed": False, "errors": 5, "time_seconds": 90}
        )
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.dimensions["dexterity"]["confidence"], 0.5)

    def test_session_status_reflects_completion(self):
        InteractionOrchestrator.record_feedback(self.session, {"completed": True, "time_seconds": 20})
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, InteractionSession.STATUS_COMPLETED)


class SessionLifecycleTests(TestCase):
    """Phase 7 section 28: a small explicit state machine — no duplicate
    completion, no COMPLETED -> STARTED, no ABANDONED -> COMPLETED."""

    def setUp(self):
        user = User.objects.create_user(username="lifecycleuser", password="x")
        task = Task.objects.create(task_id="purchase_ticket", name="Buy a ticket")
        self.session = InteractionSession.objects.create(user=user, task=task)

    def test_started_can_move_to_in_progress(self):
        self.session.transition_to(InteractionSession.STATUS_IN_PROGRESS)
        self.assertEqual(self.session.status, InteractionSession.STATUS_IN_PROGRESS)
        self.assertIsNone(self.session.completed_at)

    def test_complete_sets_terminal_status_and_completed_at(self):
        InteractionOrchestrator.complete(self.session)
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, InteractionSession.STATUS_COMPLETED)
        self.assertIsNotNone(self.session.completed_at)
        self.assertIsNotNone(self.session.completion_time_ms)

    def test_abandon_sets_terminal_status(self):
        InteractionOrchestrator.abandon(self.session, reason="user left")
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, InteractionSession.STATUS_ABANDONED)
        event = self.session.events.get(event_type=InteractionEvent.TASK_ABANDONED)
        self.assertEqual(event.metadata["reason"], "user left")

    def test_duplicate_completion_is_rejected(self):
        InteractionOrchestrator.complete(self.session)
        self.session.refresh_from_db()
        with self.assertRaises(OrchestratorError):
            InteractionOrchestrator.complete(self.session)

    def test_completed_cannot_become_abandoned(self):
        InteractionOrchestrator.complete(self.session)
        self.session.refresh_from_db()
        with self.assertRaises(OrchestratorError):
            InteractionOrchestrator.abandon(self.session)

    def test_abandoned_cannot_become_completed(self):
        InteractionOrchestrator.abandon(self.session)
        self.session.refresh_from_db()
        with self.assertRaises(OrchestratorError):
            InteractionOrchestrator.complete(self.session)


class InteractionEventTests(TestCase):
    """Phase 7 section 8/9: structured, task-relevant events only."""

    def setUp(self):
        user = User.objects.create_user(username="eventuser", password="x")
        task = Task.objects.create(task_id="purchase_ticket", name="Buy a ticket")
        self.session = InteractionSession.objects.create(user=user, task=task)

    def test_valid_event_is_recorded_and_moves_session_in_progress(self):
        InteractionOrchestrator.record_event(
            self.session, InteractionEvent.CONTROL_SELECTED, step="select_destination", control_id="dest_airport"
        )
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, InteractionSession.STATUS_IN_PROGRESS)
        self.assertEqual(self.session.events.count(), 1)

    def test_invalid_event_type_is_rejected(self):
        with self.assertRaises(OrchestratorError):
            InteractionOrchestrator.record_event(self.session, "totally_made_up_event")
        self.assertEqual(self.session.events.count(), 0)

    def test_assistance_event_increments_assistance_count(self):
        InteractionOrchestrator.record_event(self.session, InteractionEvent.ASSISTANCE_REQUESTED)
        InteractionOrchestrator.record_event(self.session, InteractionEvent.ASSISTANCE_REQUESTED)
        self.session.refresh_from_db()
        self.assertEqual(self.session.assistance_count, 2)

    def test_batched_events_are_all_recorded(self):
        events = InteractionOrchestrator.record_events(
            self.session,
            [
                {"event_type": InteractionEvent.CONTROL_SELECTED, "step": "select_destination"},
                {"event_type": InteractionEvent.CONTROL_SELECTED, "step": "select_ticket_type"},
                {"event_type": InteractionEvent.VALIDATION_ERROR, "control_id": "buy_ticket"},
            ],
        )
        self.assertEqual(len(events), 3)
        self.assertEqual(self.session.events.count(), 3)

    def test_event_metadata_is_sanitized_to_a_bounded_flat_mapping(self):
        event = InteractionOrchestrator.record_event(
            self.session,
            InteractionEvent.CONTROL_SELECTED,
            metadata={"nested": {"a": 1}, **{f"k{i}": "v" for i in range(20)}},
        )
        self.assertLessEqual(len(event.metadata), InteractionOrchestrator._MAX_METADATA_KEYS)

    def test_cannot_record_event_on_a_terminal_session(self):
        InteractionOrchestrator.complete(self.session)
        self.session.refresh_from_db()
        with self.assertRaises(OrchestratorError):
            InteractionOrchestrator.record_event(self.session, InteractionEvent.CONTROL_SELECTED)


class FeedbackValidationTests(TestCase):
    """Phase 7 section 13: controlled values only — no arbitrary
    uncontrolled ease_rating/adaptation_helpfulness."""

    def setUp(self):
        user = User.objects.create_user(username="fbvaliduser", password="x")
        task = Task.objects.create(task_id="purchase_ticket", name="Buy a ticket")
        self.session = InteractionSession.objects.create(user=user, task=task)

    def test_valid_ease_rating_is_stored(self):
        feedback = InteractionOrchestrator.record_feedback(self.session, {"completed": True, "ease_rating": 5})
        self.assertEqual(feedback.ease_rating, 5)

    def test_out_of_range_ease_rating_is_rejected(self):
        with self.assertRaises(OrchestratorError):
            InteractionOrchestrator.record_feedback(self.session, {"completed": True, "ease_rating": 7})

    def test_invalid_adaptation_helpfulness_is_rejected(self):
        with self.assertRaises(OrchestratorError):
            InteractionOrchestrator.record_feedback(
                self.session, {"completed": True, "adaptation_helpfulness": "definitely_helped"}
            )

    def test_optional_comment_is_truncated_to_max_length(self):
        long_comment = "x" * 2000
        feedback = InteractionOrchestrator.record_feedback(
            self.session, {"completed": True, "optional_comment": long_comment}
        )
        self.assertEqual(len(feedback.optional_comment), Feedback.OPTIONAL_COMMENT_MAX_LENGTH)

    def test_second_submission_updates_the_same_row_not_a_duplicate(self):
        InteractionOrchestrator.record_feedback(self.session, {"completed": True, "ease_rating": 3})
        InteractionOrchestrator.record_feedback(self.session, {"completed": True, "ease_rating": 5})
        self.assertEqual(Feedback.objects.filter(session=self.session).count(), 1)
        self.assertEqual(Feedback.objects.get(session=self.session).ease_rating, 5)

    def test_feedback_after_explicit_complete_does_not_change_terminal_status(self):
        InteractionOrchestrator.complete(self.session)
        self.session.refresh_from_db()
        InteractionOrchestrator.record_feedback(self.session, {"completed": False, "ease_rating": 4})
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, InteractionSession.STATUS_COMPLETED)
