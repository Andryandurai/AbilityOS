"""InteractionOrchestrator — coordinates the AbilityOS core loop (Part 5, Part 17).

Each public method here corresponds to one stage of the workflow table in
Part 5 and one REST endpoint in Part 11/api.views. Keeping this logic out of
the Django views means the views stay thin and the pipeline stays testable
without an HTTP client.
"""

from __future__ import annotations

import copy
import logging

from django.db import transaction
from django.shortcuts import get_object_or_404

from abilities.models import AbilityProfile
from adaptations.models import Adaptation, AdaptationResult
from adaptations.services.rules import validate_adaptation
from ai_engine.services import vision_service
from ai_engine.services.decision_engine import decide
from analytics import services as analytics_services
from barriers.models import Barrier
from barriers.services.detection import detect_and_save
from environments.models import Environment
from feedback.models import Feedback, InteractionEvent, InteractionSession
from tasks.models import Task
from users.services.consent_service import is_consented_for_adaptation

logger = logging.getLogger("api")

DEFAULT_ENVIRONMENT_ID = "kiosk_standard"


class OrchestratorError(Exception):
    """Raised for invalid workflow transitions (e.g. detecting barriers
    before an environment has been attached to the session)."""


class InteractionOrchestrator:
    # ------------------------------------------------------------------
    # Step 1-4: start a session against a user/task/environment
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def start(user, task_id: str, environment_id: str | None = None, baseline_mode: bool = False) -> InteractionSession:
        if not is_consented_for_adaptation(user):
            raise OrchestratorError(
                "Consent required before AbilityOS can use this profile for interaction "
                "adaptation. Grant consent via POST /api/users/{id}/consent/ first."
            )

        task = get_object_or_404(Task, task_id=task_id)
        environment = None
        env_id = environment_id or DEFAULT_ENVIRONMENT_ID
        environment = Environment.objects.filter(environment_id=env_id).first()

        profile, _ = AbilityProfile.objects.get_or_create(user=user)

        session = InteractionSession.objects.create(
            user=user,
            task=task,
            environment=environment,
            status=InteractionSession.STATUS_STARTED,
            baseline_mode=baseline_mode,
            ability_profile_snapshot=copy.deepcopy(profile.dimensions),
        )
        return session

    # ------------------------------------------------------------------
    # Step 4: environment understanding
    # ------------------------------------------------------------------
    @staticmethod
    def analyze_environment(session: InteractionSession, image_base64: str | None = None) -> Environment:
        if image_base64 and vision_service.is_configured():
            try:
                data = vision_service.analyze_screenshot(image_base64)
                env = Environment.objects.create(
                    environment_id=f"vision_{session.pk}",
                    name=f"Vision-captured environment for session {session.pk}",
                    source=Environment.SOURCE_VISION,
                    data=data,
                )
                session.environment = env
                session.status = InteractionSession.STATUS_ANALYZED
                session.save(update_fields=["environment", "status", "updated_at"])
                return env
            except vision_service.VisionUnavailableError as exc:
                logger.info("Vision analysis unavailable, using fixture environment: %s", exc)

        if session.environment is None:
            session.environment = Environment.objects.filter(
                environment_id=DEFAULT_ENVIRONMENT_ID
            ).first()

        session.status = InteractionSession.STATUS_ANALYZED
        session.save(update_fields=["environment", "status", "updated_at"])
        return session.environment

    # ------------------------------------------------------------------
    # Step 5: barrier detection
    # ------------------------------------------------------------------
    @staticmethod
    def detect_barriers(session: InteractionSession) -> list[Barrier]:
        if session.environment is None:
            raise OrchestratorError("Cannot detect barriers before an environment is attached.")

        profile = AbilityProfile.objects.get(user=session.user)
        session.barriers.all().delete()
        barriers = detect_and_save(session, profile, session.task, session.environment)
        return barriers

    # ------------------------------------------------------------------
    # Steps 6-8: candidate generation, AI reasoning, safety validation
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def recommend_adaptations(session: InteractionSession) -> list[AdaptationResult]:
        barriers = list(session.barriers.all())
        if not barriers:
            return []

        profile = AbilityProfile.objects.get(user=session.user)
        outcome = decide(barriers, session.task, profile)

        AdaptationResult.objects.filter(session=session).delete()
        results = []
        for d in outcome.decisions:
            validation = validate_adaptation(d.adaptation, session.task.task_id)
            rationale = d.rationale
            if not validation.approved:
                rationale = f"{rationale} [REJECTED by rule engine: {validation.reason}]"

            result = AdaptationResult.objects.create(
                session=session,
                barrier=d.barrier,
                adaptation=d.adaptation,
                score=d.score,
                score_breakdown={**d.breakdown, "ai_confidence": d.ai_confidence},
                rationale=rationale,
                source=d.source,
                candidates_considered=d.candidates_considered,
                approved=validation.approved,
                requires_confirmation=validation.requires_confirmation,
            )
            results.append(result)

        session.ai_used = outcome.ai_used
        session.save(update_fields=["ai_used", "updated_at"])
        return results

    # ------------------------------------------------------------------
    # Step 9: apply the approved adaptation(s) to the interface
    # ------------------------------------------------------------------
    @staticmethod
    def apply(session: InteractionSession, confirmed_ids: list[int] | None = None) -> dict:
        confirmed_ids = set(confirmed_ids or [])
        applied_results = []

        if not session.baseline_mode:
            for result in session.adaptation_results.select_related("adaptation").all():
                if not result.approved:
                    continue
                if result.requires_confirmation and result.pk not in confirmed_ids and not result.confirmed:
                    continue
                if result.pk in confirmed_ids:
                    result.confirmed = True
                result.applied = True
                result.save(update_fields=["confirmed", "applied"])
                applied_results.append(result)

        merged_effects: dict = {}
        for result in applied_results:
            merged_effects.update(result.adaptation.ui_effects)

        session.status = InteractionSession.STATUS_ADAPTED
        session.save(update_fields=["status", "updated_at"])

        return {
            "applied_adaptations": [r.adaptation.name for r in applied_results],
            "ui_effects": merged_effects,
            "baseline_mode": session.baseline_mode,
        }

    # ------------------------------------------------------------------
    # Phase 7: step-level interaction events
    # ------------------------------------------------------------------
    _VALID_EVENT_TYPES = {choice[0] for choice in InteractionEvent.EVENT_TYPE_CHOICES}
    _MAX_METADATA_KEYS = 10
    _MAX_METADATA_VALUE_LENGTH = 200

    @staticmethod
    def _sanitize_metadata(metadata) -> dict:
        """Privacy-by-design (Phase 7 section 9): structured, bounded
        metadata only — never raw input. Silently drops anything that
        isn't a small flat mapping rather than persisting arbitrary data."""

        if not isinstance(metadata, dict):
            return {}
        clean: dict = {}
        for key, value in list(metadata.items())[: InteractionOrchestrator._MAX_METADATA_KEYS]:
            if not isinstance(key, str):
                continue
            clean[key[:60]] = str(value)[: InteractionOrchestrator._MAX_METADATA_VALUE_LENGTH]
        return clean

    @staticmethod
    @transaction.atomic
    def record_event(
        session: InteractionSession, event_type: str, step: str = "", control_id: str = "", metadata: dict | None = None
    ) -> InteractionEvent:
        if event_type not in InteractionOrchestrator._VALID_EVENT_TYPES:
            raise OrchestratorError(f"Unknown event_type: '{event_type}'.")
        if session.status in InteractionSession.TERMINAL_STATUSES:
            raise OrchestratorError(f"Cannot record an event on a {session.status} session.")

        event = InteractionEvent.objects.create(
            session=session,
            event_type=event_type,
            step=(step or "")[:80],
            control_id=(control_id or "")[:80],
            metadata=InteractionOrchestrator._sanitize_metadata(metadata),
        )

        update_fields = []
        if session.status in {
            InteractionSession.STATUS_STARTED,
            InteractionSession.STATUS_ANALYZED,
            InteractionSession.STATUS_ADAPTED,
        }:
            session.transition_to(InteractionSession.STATUS_IN_PROGRESS)
            update_fields.append("status")
        if event_type == InteractionEvent.ASSISTANCE_REQUESTED:
            session.assistance_count += 1
            update_fields.append("assistance_count")
        if update_fields:
            session.save(update_fields=update_fields + ["updated_at"])

        return event

    @staticmethod
    def record_events(session: InteractionSession, events: list[dict]) -> list[InteractionEvent]:
        """Batched form (Phase 7 section 29): the frontend accumulates
        events locally and flushes them in one call rather than one HTTP
        request per tap."""
        return [
            InteractionOrchestrator.record_event(
                session,
                e.get("event_type"),
                step=e.get("step", ""),
                control_id=e.get("control_id", ""),
                metadata=e.get("metadata"),
            )
            for e in events
        ]

    # ------------------------------------------------------------------
    # Phase 7: explicit session completion / abandonment
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def complete(session: InteractionSession) -> InteractionSession:
        try:
            session.transition_to(InteractionSession.STATUS_COMPLETED)
        except ValueError as exc:
            raise OrchestratorError(str(exc)) from exc
        session.save(update_fields=["status", "completed_at", "updated_at"])
        InteractionEvent.objects.create(session=session, event_type=InteractionEvent.TASK_COMPLETED)
        return session

    @staticmethod
    @transaction.atomic
    def abandon(session: InteractionSession, reason: str = "") -> InteractionSession:
        try:
            session.transition_to(InteractionSession.STATUS_ABANDONED)
        except ValueError as exc:
            raise OrchestratorError(str(exc)) from exc
        session.save(update_fields=["status", "completed_at", "updated_at"])
        InteractionEvent.objects.create(
            session=session,
            event_type=InteractionEvent.TASK_ABANDONED,
            metadata={"reason": reason[:200]} if reason else {},
        )
        return session

    # ------------------------------------------------------------------
    # Steps 10-12: feedback (Phase 7 extends this with the short, subjective
    # feedback screen's fields; see docs/PHASE_7.md "Learning Signal" for
    # why the previous automatic profile-confidence nudge was retired here)
    # ------------------------------------------------------------------
    @staticmethod
    @transaction.atomic
    def record_feedback(session: InteractionSession, data: dict) -> Feedback:
        defaults = {
            "completed": data.get("completed", False),
            "errors": data.get("errors", 0),
            "time_seconds": data.get("time_seconds", 0),
            "assistance_requested": data.get("assistance_requested", False),
            "effort": data.get("effort", 3),
            "confidence": data.get("confidence", 3),
        }

        if data.get("ease_rating") is not None:
            ease_rating = data["ease_rating"]
            if ease_rating not in dict(Feedback.EASE_CHOICES):
                raise OrchestratorError(f"Invalid ease_rating: {ease_rating!r}. Allowed: 1-5.")
            defaults["ease_rating"] = ease_rating

        if data.get("adaptation_helpfulness"):
            helpfulness = data["adaptation_helpfulness"]
            if helpfulness not in dict(Feedback.HELPFULNESS_CHOICES):
                raise OrchestratorError(f"Invalid adaptation_helpfulness: {helpfulness!r}.")
            defaults["adaptation_helpfulness"] = helpfulness

        if data.get("optional_comment"):
            defaults["optional_comment"] = str(data["optional_comment"])[: Feedback.OPTIONAL_COMMENT_MAX_LENGTH]

        feedback, _ = Feedback.objects.update_or_create(session=session, defaults=defaults)

        # Backward-compatible completion: if nothing has already moved this
        # session to a terminal status via the new explicit complete()/
        # abandon() calls, feedback submission itself still does so — the
        # single-call flow every pre-Phase-7 test and the old frontend used
        # keeps working unchanged.
        if session.status not in InteractionSession.TERMINAL_STATUSES:
            target = InteractionSession.STATUS_COMPLETED if feedback.completed else InteractionSession.STATUS_ABANDONED
            session.transition_to(target)
            session.save(update_fields=["status", "completed_at", "updated_at"])

        return feedback

    # ------------------------------------------------------------------
    # Summary for the developer/explanation panel
    # ------------------------------------------------------------------
    @staticmethod
    def summary(session: InteractionSession) -> dict:
        barriers = list(session.barriers.all())
        results = list(session.adaptation_results.select_related("adaptation", "barrier").all())
        feedback = getattr(session, "feedback", None)

        interaction_counts = analytics_services.session_interaction_counts(session)
        outcome_score = analytics_services.calculate_outcome_score(session, feedback) if feedback else None
        learning_signal = analytics_services.generate_learning_signal(session, feedback)

        return {
            "session_id": session.pk,
            "status": session.status,
            "baseline_mode": session.baseline_mode,
            "experience_mode": session.experience_mode,
            "ai_used": session.ai_used,
            "assistance_count": session.assistance_count,
            "completion_time_ms": session.completion_time_ms,
            "interaction_counts": interaction_counts,
            "user": {"id": session.user_id, "username": session.user.username},
            "task": {"task_id": session.task.task_id, "name": session.task.name},
            "environment": (
                {
                    "environment_id": session.environment.environment_id,
                    "source": session.environment.source,
                    "data": session.environment.data,
                }
                if session.environment
                else None
            ),
            "ability_profile_snapshot": session.ability_profile_snapshot,
            "barriers": [
                {
                    "id": b.pk,
                    "type": b.barrier_type,
                    "ability_dimension": b.ability_dimension,
                    "severity": b.severity,
                    "confidence": b.confidence,
                    "evidence": b.evidence,
                }
                for b in barriers
            ],
            "adaptation_results": [
                {
                    "id": r.pk,
                    "barrier_type": r.barrier.barrier_type,
                    "adaptation": r.adaptation.name,
                    "display_name": r.adaptation.display_name,
                    "score": r.score,
                    "score_breakdown": r.score_breakdown,
                    "rationale": r.rationale,
                    "source": r.source,
                    "approved": r.approved,
                    "requires_confirmation": r.requires_confirmation,
                    "confirmed": r.confirmed,
                    "applied": r.applied,
                    "ui_effects": r.adaptation.ui_effects,
                    "candidates_considered": r.candidates_considered,
                }
                for r in results
            ],
            "feedback": (
                {
                    "completed": feedback.completed,
                    "errors": feedback.errors,
                    "time_seconds": feedback.time_seconds,
                    "assistance_requested": feedback.assistance_requested,
                    "effort": feedback.effort,
                    "confidence": feedback.confidence,
                    "ease_rating": feedback.ease_rating,
                    "adaptation_helpfulness": feedback.adaptation_helpfulness,
                    "optional_comment": feedback.optional_comment,
                }
                if feedback
                else None
            ),
            "outcome_score": outcome_score,
            "learning_signal": learning_signal,
        }
