from django.conf import settings
from django.db import models

__all__ = ["QuestionnaireQuestion", "QuestionnaireSession", "QuestionnaireResponse"]


class QuestionnaireQuestion(models.Model):
    """One versioned question in the functional ability questionnaire.

    A "front door" onto the existing, authoritative
    abilities.constants.ALLOWED_LEVELS vocabulary -- `key` must be one of
    abilities.constants.DIMENSION_KEYS and every option's `value` must be
    one of abilities.constants.ALLOWED_LEVELS[key] (enforced at seed time
    by questionnaire.management.commands.seed_questionnaire, and again at
    answer time by questionnaire.services.questionnaire_service -- never
    trusted from either the stored row alone or the frontend). This model
    stores question *text* only; it is never itself read by barrier
    detection, adaptation scoring, or any other part of the AbilityOS
    reasoning core.
    """

    SINGLE_CHOICE = "single_choice"
    QUESTION_TYPE_CHOICES = [(SINGLE_CHOICE, "Single choice")]

    key = models.CharField(
        max_length=40, help_text="Must match an abilities.constants.DIMENSION_KEYS entry."
    )
    version = models.PositiveIntegerField(default=1)
    question_text = models.CharField(max_length=300)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPE_CHOICES, default=SINGLE_CHOICE)
    order = models.PositiveIntegerField()
    options = models.JSONField(
        default=list, help_text='[{"value": "<ALLOWED_LEVELS[key] entry>", "label": "<display text>"}, ...]'
    )

    class Meta:
        ordering = ["version", "order"]
        constraints = [
            models.UniqueConstraint(fields=["key", "version"], name="one_question_per_key_per_version"),
        ]

    def __str__(self):
        return f"QuestionnaireQuestion<{self.key} v{self.version}>"


class QuestionnaireSession(models.Model):
    """One questionnaire attempt for one authenticated user. A user may
    have many (Phase 2 section 7's "future re-taking" note) -- a plain
    ForeignKey, the same shape feedback.InteractionSession already uses for
    "one user, many sessions" (Phase 0 audit section 5)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="questionnaire_sessions"
    )
    version = models.PositiveIntegerField(help_text="The question-set version this session was started with.")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    @property
    def is_completed(self) -> bool:
        return self.completed_at is not None

    def __str__(self):
        return f"QuestionnaireSession<user={self.user_id} v{self.version}>"


class QuestionnaireResponse(models.Model):
    """One answer to one question within one session. `selected_value` is
    stored as given, but is never trusted as-is -- every read path
    (build_dimensions_from_responses) re-validates it against
    ALLOWED_LEVELS before it can become part of a dimensions payload."""

    session = models.ForeignKey(QuestionnaireSession, on_delete=models.CASCADE, related_name="responses")
    question = models.ForeignKey(QuestionnaireQuestion, on_delete=models.PROTECT, related_name="responses")
    selected_value = models.CharField(max_length=60)
    answered_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "question"], name="one_response_per_question_per_session"),
        ]

    def __str__(self):
        return f"QuestionnaireResponse<session={self.session_id} question={self.question_id}>"
