"""Questionnaire business logic (Phase 2).

Kept out of the view layer, mirroring abilities.services.profile_service's
existing separation in this codebase: View -> Serializer validation ->
this service -> abilities.services.profile_service. This module never
writes to AbilityProfile directly -- confirm_questionnaire() is the one
function that touches a profile, and it does so exclusively by calling
apply_manual_update(), the same authoritative write path the manual
profile editor already uses. There is no second write path into
AbilityProfile anywhere in this app.
"""

from __future__ import annotations

from django.utils import timezone

from abilities.constants import ALLOWED_LEVELS, DIMENSION_KEYS
from abilities.services.profile_service import apply_manual_update, get_or_create_profile
from questionnaire.models import QuestionnaireQuestion, QuestionnaireResponse, QuestionnaireSession


class QuestionnaireError(ValueError):
    """Raised for any questionnaire operation that violates its own rules
    (unknown question, invalid value, incomplete answers, an
    already-completed session used incorrectly) -- mirrors
    abilities.services.profile_service.ProfileValidationError's role in
    this codebase: a message naming the exact problem, never a silent
    coercion."""


def current_version() -> int:
    """The questionnaire has no separate "QuestionnaireVersion" model
    (Phase 2 section 7: "do not create unnecessary complexity") -- the
    current version is simply the highest version any question was seeded
    at. Defaults to 1 if nothing has been seeded yet."""

    latest = QuestionnaireQuestion.objects.order_by("-version").values_list("version", flat=True).first()
    return latest or 1


def get_questionnaire(version: int | None = None) -> tuple[int, list[QuestionnaireQuestion]]:
    version = version or current_version()
    questions = list(QuestionnaireQuestion.objects.filter(version=version).order_by("order"))
    return version, questions


def start_questionnaire(user) -> QuestionnaireSession:
    """A session always captures *today's* current version and keeps it
    for its whole lifetime (Phase 2 section 8) -- if the question set
    changes later, an in-progress or already-completed session is never
    silently reinterpreted against a newer version."""

    return QuestionnaireSession.objects.create(user=user, version=current_version())


def _validate_value(question: QuestionnaireQuestion, selected_value) -> None:
    """Never trusts the frontend, and never trusts the question's own
    stored `options` JSON alone either -- re-checks against
    abilities.constants, the single source of truth every other layer of
    this codebase already reads from (Phase 2 section 9)."""

    if not isinstance(selected_value, str):
        raise QuestionnaireError("selected_value must be a string.")
    if question.key not in DIMENSION_KEYS:
        raise QuestionnaireError(f"Question key '{question.key}' is not a recognized ability dimension.")
    if selected_value not in ALLOWED_LEVELS[question.key]:
        allowed = ", ".join(ALLOWED_LEVELS[question.key])
        raise QuestionnaireError(f"'{selected_value}' is not a valid value for '{question.key}'. Allowed: {allowed}.")


def save_response(session: QuestionnaireSession, question_id, selected_value: str) -> QuestionnaireResponse:
    if session.is_completed:
        raise QuestionnaireError("This questionnaire has already been completed and can no longer be answered.")

    try:
        question = QuestionnaireQuestion.objects.get(pk=question_id, version=session.version)
    except (QuestionnaireQuestion.DoesNotExist, ValueError, TypeError) as exc:
        raise QuestionnaireError("Unknown question for this questionnaire session's version.") from exc

    _validate_value(question, selected_value)

    response, _ = QuestionnaireResponse.objects.update_or_create(
        session=session, question=question, defaults={"selected_value": selected_value}
    )
    return response


def build_dimensions_from_responses(session: QuestionnaireSession) -> dict:
    """The entire response -> dimension mapping (Phase 2 section 11):
    QuestionnaireQuestion.key becomes the dimensions dict key,
    QuestionnaireResponse.selected_value becomes {"level": ...} -- no
    scoring, no inference, no combining multiple answers into one
    dimension. Re-validates every answer against ALLOWED_LEVELS again here
    (defense in depth -- a row could in principle have been written before
    a vocabulary change), so a tampered or stale value can never reach
    AbilityProfile.dimensions."""

    questions = list(QuestionnaireQuestion.objects.filter(version=session.version).order_by("order"))
    responses_by_question = {r.question_id: r for r in session.responses.select_related("question")}

    missing = [q.key for q in questions if q.id not in responses_by_question]
    if missing:
        raise QuestionnaireError(f"Missing answers for: {', '.join(missing)}.")

    dimensions = {}
    for question in questions:
        response = responses_by_question[question.id]
        _validate_value(question, response.selected_value)
        dimensions[question.key] = {"level": response.selected_value}
    return dimensions


def complete_questionnaire(session: QuestionnaireSession) -> dict:
    """Validates every answer and returns the generated `dimensions` dict
    -- deliberately does NOT write to AbilityProfile (Phase 2 section 14).
    Marks the session completed (locking out further save_response calls)
    so the answers a person reviews are exactly the answers that get
    confirmed, not a moving target. Safe to call again on an
    already-completed session (idempotent) -- e.g. the frontend re-showing
    the review screen after a page refresh."""

    dimensions = build_dimensions_from_responses(session)
    if not session.is_completed:
        session.completed_at = timezone.now()
        session.save(update_fields=["completed_at"])
    return dimensions


def confirm_questionnaire(session: QuestionnaireSession):
    """The one function in this entire app that touches AbilityProfile --
    and it does so exclusively via abilities.services.profile_service.
    apply_manual_update(), the same authoritative write path the manual
    profile editor already uses (Phase 2 sections 3/13/33). `dimensions` is
    always re-derived fresh from the session's stored responses here, never
    accepted as a parameter from the caller -- a confirm request can only
    ever commit what was actually answered and already validated by
    complete_questionnaire(), never an arbitrary client-supplied payload.
    """

    if not session.is_completed:
        raise QuestionnaireError("Complete the questionnaire before confirming the generated profile.")

    dimensions = build_dimensions_from_responses(session)
    profile = get_or_create_profile(session.user)
    return apply_manual_update(profile, dimensions=dimensions)
