from django.conf import settings
from django.db import models
from django.utils import timezone


class InteractionSession(models.Model):
    """One person-task-environment interaction (Part 5, Part 10).

    This is the row that ties together the user, the task, the environment,
    the barriers detected, the adaptation(s) chosen, and the eventual
    feedback — the same row the analytics module aggregates over.

    Phase 7 note on snapshots (avoids duplicating the whole user record):
    `ability_profile_snapshot` already captures what Phase 7's spec calls
    the "barrier_snapshot"/"approved_adaptation" concern at the right
    granularity — the `Barrier` and `AdaptationResult` rows this session
    owns (via FK, `on_delete=CASCADE`/`PROTECT`) are themselves immutable
    once created and already scoped to this session, so they already serve
    as that historical record without a second, redundant copy of the same
    facts on this model.
    """

    STATUS_STARTED = "started"
    STATUS_ANALYZED = "analyzed"
    STATUS_ADAPTED = "adapted"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_COMPLETED = "completed"
    STATUS_ABANDONED = "abandoned"
    STATUS_FAILED = "failed"

    STATUS_CHOICES = [
        (STATUS_STARTED, "Started"),
        (STATUS_ANALYZED, "Analyzed"),
        (STATUS_ADAPTED, "Adapted"),
        (STATUS_IN_PROGRESS, "In progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_ABANDONED, "Abandoned"),
        (STATUS_FAILED, "Failed"),
    ]

    TERMINAL_STATUSES = {STATUS_COMPLETED, STATUS_ABANDONED, STATUS_FAILED}

    # Phase 7 section 28: a small, explicit state machine. Every non-terminal
    # status may move forward to `in_progress` or straight to a terminal
    # status (a session can be abandoned/fail before any step interaction is
    # recorded); once terminal, a session never leaves that state — no
    # duplicate completion, no COMPLETED -> STARTED, no ABANDONED -> COMPLETED.
    VALID_TRANSITIONS = {
        STATUS_STARTED: {STATUS_ANALYZED, STATUS_ADAPTED, STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_ABANDONED, STATUS_FAILED},
        STATUS_ANALYZED: {STATUS_ADAPTED, STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_ABANDONED, STATUS_FAILED},
        STATUS_ADAPTED: {STATUS_IN_PROGRESS, STATUS_COMPLETED, STATUS_ABANDONED, STATUS_FAILED},
        STATUS_IN_PROGRESS: {STATUS_COMPLETED, STATUS_ABANDONED, STATUS_FAILED},
        STATUS_COMPLETED: set(),
        STATUS_ABANDONED: set(),
        STATUS_FAILED: set(),
    }

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interaction_sessions"
    )
    task = models.ForeignKey("tasks.Task", on_delete=models.CASCADE, related_name="sessions")
    environment = models.ForeignKey(
        "environments.Environment", on_delete=models.SET_NULL, null=True, related_name="sessions"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_STARTED)
    ai_used = models.BooleanField(default=False)
    baseline_mode = models.BooleanField(
        default=False,
        help_text="True = barriers are detected but no adaptation is applied, so this "
        "session can feed the 'without AbilityOS' side of the before/after metrics. "
        "Equivalent to Phase 7's 'experience_mode': standard=True, adaptive=False.",
    )
    is_seed = models.BooleanField(
        default=False, help_text="True for demo data created by seed_demo, not a live session."
    )
    ability_profile_snapshot = models.JSONField(
        default=dict, help_text="Copy of AbilityProfile.dimensions at session start, for audit."
    )
    assistance_count = models.PositiveIntegerField(
        default=0, help_text="Number of explicit assistance-requested events recorded this session."
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="Server timestamp when the session reached a terminal status."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["baseline_mode"]),
            models.Index(fields=["task", "status"]),
        ]

    def __str__(self):
        return f"Session#{self.pk} {self.user} / {self.task.task_id} [{self.status}]"

    @property
    def experience_mode(self) -> str:
        return "standard" if self.baseline_mode else "adaptive"

    @property
    def completion_time_ms(self) -> int | None:
        """Server-authoritative duration (Phase 7 section 10) — computed
        from `created_at`/`completed_at`, never trusted from the frontend
        alone."""
        if not self.completed_at:
            return None
        return int((self.completed_at - self.created_at).total_seconds() * 1000)

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.VALID_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status: str) -> None:
        """Raises ValueError on an invalid transition — including a
        same-status call once terminal — rather than silently allowing a
        duplicate completion event (Phase 7 section 28)."""
        if not self.can_transition_to(new_status):
            raise ValueError(f"Invalid session transition: {self.status} -> {new_status}")
        self.status = new_status
        if new_status in self.TERMINAL_STATUSES:
            self.completed_at = timezone.now()


class Feedback(models.Model):
    """Outcome metrics for a session (Part 5 step 11, Part 18/20), extended
    in Phase 7 with the short, controlled-vocabulary user-facing feedback
    screen (section 12/13): ease, adaptation helpfulness, and an optional
    comment. `assistance_requested` already means exactly what Phase 7's
    spec calls `assistance_required` ("did you need a person's help?") —
    it's fed by the kiosk's explicit "Ask for help" control either way, so
    it is reused rather than duplicated under a second name.

    `effort`/`confidence` are the pre-existing self-reported fields from an
    earlier pass; Phase 7 keeps them (no data loss, no breaking migration)
    but no longer derives anything automatically from them — see
    `docs/PHASE_7.md` "Learning Signal" for why the old auto-confidence
    hook was retired this phase.
    """

    EASE_VERY_DIFFICULT = 1
    EASE_DIFFICULT = 2
    EASE_OKAY = 3
    EASE_EASY = 4
    EASE_VERY_EASY = 5

    EASE_CHOICES = [
        (EASE_VERY_DIFFICULT, "Very difficult"),
        (EASE_DIFFICULT, "Difficult"),
        (EASE_OKAY, "Okay"),
        (EASE_EASY, "Easy"),
        (EASE_VERY_EASY, "Very easy"),
    ]

    HELPED = "helped"
    SOMEWHAT_HELPED = "somewhat_helped"
    DID_NOT_HELP = "did_not_help"

    HELPFULNESS_CHOICES = [
        (HELPED, "Yes, it helped"),
        (SOMEWHAT_HELPED, "Somewhat"),
        (DID_NOT_HELP, "No, it did not help"),
    ]

    OPTIONAL_COMMENT_MAX_LENGTH = 500

    session = models.OneToOneField(
        InteractionSession, on_delete=models.CASCADE, related_name="feedback"
    )
    completed = models.BooleanField(default=False)
    errors = models.PositiveIntegerField(default=0)
    time_seconds = models.PositiveIntegerField(default=0)
    assistance_requested = models.BooleanField(default=False)
    effort = models.PositiveSmallIntegerField(
        default=3, help_text="Self-reported effort, 1 (low) - 5 (high)."
    )
    confidence = models.PositiveSmallIntegerField(
        default=3, help_text="Self-reported confidence, 1 (low) - 5 (high)."
    )
    ease_rating = models.PositiveSmallIntegerField(
        null=True, blank=True, choices=EASE_CHOICES, help_text="1 (very difficult) - 5 (very easy)."
    )
    adaptation_helpfulness = models.CharField(
        max_length=20, blank=True, choices=HELPFULNESS_CHOICES,
        help_text="Only meaningful when an adaptation was actually applied this session.",
    )
    optional_comment = models.CharField(max_length=OPTIONAL_COMMENT_MAX_LENGTH, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback<session={self.session_id} completed={self.completed}>"


class InteractionEvent(models.Model):
    """One task-relevant interaction moment within a session (Phase 7
    section 8) — structured metadata only, never raw input: no keystrokes,
    no audio, no video. Used to derive granular counts (retries, backtracks,
    validation errors, assistance requests) without inflating `Feedback`
    or `InteractionSession` with fields that are really just aggregates of
    these rows.
    """

    STEP_STARTED = "step_started"
    CONTROL_SELECTED = "control_selected"
    CONTROL_RESELECTED = "control_reselected"
    VALIDATION_ERROR = "validation_error"
    BACK_NAVIGATION = "back_navigation"
    CONFIRMATION_OPENED = "confirmation_opened"
    CONFIRMATION_COMPLETED = "confirmation_completed"
    ASSISTANCE_REQUESTED = "assistance_requested"
    TASK_COMPLETED = "task_completed"
    TASK_ABANDONED = "task_abandoned"
    INTERACTION_TIMEOUT = "interaction_timeout"

    EVENT_TYPE_CHOICES = [
        (STEP_STARTED, "Step started"),
        (CONTROL_SELECTED, "Control selected"),
        (CONTROL_RESELECTED, "Control re-selected (retry)"),
        (VALIDATION_ERROR, "Validation error"),
        (BACK_NAVIGATION, "Back navigation"),
        (CONFIRMATION_OPENED, "Confirmation opened"),
        (CONFIRMATION_COMPLETED, "Confirmation completed"),
        (ASSISTANCE_REQUESTED, "Assistance requested"),
        (TASK_COMPLETED, "Task completed"),
        (TASK_ABANDONED, "Task abandoned"),
        (INTERACTION_TIMEOUT, "Interaction timed out"),
    ]

    RETRY_EVENT_TYPES = {CONTROL_RESELECTED}
    ERROR_EVENT_TYPES = {VALIDATION_ERROR}
    BACKTRACK_EVENT_TYPES = {BACK_NAVIGATION}
    TIMEOUT_EVENT_TYPES = {INTERACTION_TIMEOUT}

    session = models.ForeignKey(InteractionSession, on_delete=models.CASCADE, related_name="events")
    step = models.CharField(max_length=80, blank=True)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    control_id = models.CharField(max_length=80, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["session", "event_type"])]

    def __str__(self):
        return f"InteractionEvent<{self.event_type} session={self.session_id}>"
