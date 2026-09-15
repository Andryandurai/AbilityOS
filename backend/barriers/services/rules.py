"""Barrier rules (Phase 4).

Each rule answers exactly one question — "does this specific mismatch
exist?" — using only the AbilityProfile/TaskDescriptor/EnvironmentDescriptor
facts it's given. No Django model access, no HTTP request object, no I/O:
plain functions over plain dicts, so every rule is independently unit-
testable and the detector can run them without touching the database.

Deterministic only: same three inputs -> same output, every time. No LLM,
no ML, no randomness, no external API call.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from barriers.services.config import (
    COGNITION_BASE_SEVERITY,
    COGNITION_TRIGGER_LEVELS,
    DEXTERITY_BASE_SEVERITY,
    DEXTERITY_TRIGGER_LEVELS,
    HEARING_BASE_SEVERITY,
    HEARING_TRIGGER_LEVELS,
    MAX_SIMULTANEOUS_CHOICES,
    MIN_CONTRAST_RATIO,
    MIN_TAP_TARGET_HEIGHT,
    MIN_TAP_TARGET_WIDTH,
    VISION_CONTRAST_TRIGGER_LEVELS,
    clamp,
)
from barriers.services.result import BarrierResult


class BarrierRule(ABC):
    barrier_type: str
    ability_dimension: str

    @abstractmethod
    def detect(self, ability_profile: dict, task: dict, environment: dict) -> list[BarrierResult]:
        """Returns zero or more BarrierResults. Never raises for merely
        "no barrier found" — that's an empty list, a perfectly valid and
        expected outcome (Phase 4 spec section 22)."""


def _dimension(ability_profile: dict, key: str) -> dict:
    return ability_profile.get(key) or {"level": "typical", "confidence": 0.5}


def _task_relevant_controls(task: dict, environment: dict) -> list[dict]:
    """Prefers controls that are relevant to the task at hand (matched by id
    against the task's own control list — Phase 4 spec section 24: "prefer
    Task control + Environment control matching by ID"). Falls back to every
    environment control if the two happen to share no ids at all, so a rule
    never silently evaluates nothing just because two independently-built
    fixtures used different naming."""

    env_controls = environment.get("controls") or []
    task_control_ids = {c.get("id") for c in (task.get("controls") or [])}
    matched = [c for c in env_controls if c.get("id") in task_control_ids]
    return matched or env_controls


class SmallTapTargetRule(BarrierRule):
    barrier_type = "small_tap_targets"
    ability_dimension = "dexterity"

    def detect(self, ability_profile, task, environment):
        dexterity = _dimension(ability_profile, "dexterity")
        level = dexterity.get("level")
        if level not in DEXTERITY_TRIGGER_LEVELS:
            return []

        controls = _task_relevant_controls(task, environment)
        undersized = [
            c
            for c in controls
            if c.get("width") is not None
            and c.get("height") is not None
            and (c["width"] < MIN_TAP_TARGET_WIDTH or c["height"] < MIN_TAP_TARGET_HEIGHT)
        ]
        if not undersized:
            return []

        # Severity formula: start from how severe this dexterity level is on
        # its own, then scale up toward 1.0 by how far the worst offending
        # control falls below the threshold. A control right at the
        # threshold contributes ~0 extra severity; one at half the
        # threshold pushes severity close to 1.0.
        worst = min(undersized, key=lambda c: min(c["width"] / MIN_TAP_TARGET_WIDTH, c["height"] / MIN_TAP_TARGET_HEIGHT))
        size_ratio = min(worst["width"] / MIN_TAP_TARGET_WIDTH, worst["height"] / MIN_TAP_TARGET_HEIGHT, 1.0)
        shortfall = 1.0 - size_ratio
        base = DEXTERITY_BASE_SEVERITY.get(level, 0.5)
        severity = clamp(base + shortfall * (1 - base))

        return [
            BarrierResult(
                barrier_type=self.barrier_type,
                ability_dimension=self.ability_dimension,
                severity=severity,
                confidence=dexterity.get("confidence", 0.5),
                title="Small touch targets",
                description=(
                    "Several interactive controls are below the configured minimum "
                    f"touch target size ({MIN_TAP_TARGET_WIDTH}x{MIN_TAP_TARGET_HEIGHT}px) "
                    f"for a '{level}' dexterity profile."
                ),
                evidence={
                    "controls": [
                        {"id": c.get("id"), "width": c.get("width"), "height": c.get("height")}
                        for c in undersized
                    ],
                    "threshold": {"min_width": MIN_TAP_TARGET_WIDTH, "min_height": MIN_TAP_TARGET_HEIGHT},
                    "ability_value": level,
                },
            )
        ]


def _hex_to_relative_luminance(hex_color: str) -> float:
    """WCAG 2.1 relative luminance — a standard, externally-defined formula,
    not an invented measurement (Phase 4 spec section 10)."""

    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    def channel(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = channel(r), channel(g), channel(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(hex1: str, hex2: str) -> float:
    l1, l2 = _hex_to_relative_luminance(hex1), _hex_to_relative_luminance(hex2)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


class LowContrastTextRule(BarrierRule):
    barrier_type = "low_contrast_text"
    ability_dimension = "vision"

    def detect(self, ability_profile, task, environment):
        vision = _dimension(ability_profile, "vision")
        level = vision.get("level")
        if level not in VISION_CONTRAST_TRIGGER_LEVELS:
            return []

        contrast = environment.get("contrast")
        ratio = None
        source = None

        if isinstance(contrast, dict) and contrast.get("background") and contrast.get("foreground"):
            ratio = _contrast_ratio(contrast["background"], contrast["foreground"])
            source = "computed"
        elif isinstance(contrast, dict) and contrast.get("level") == "low":
            # No actual colors to compute from — use the fixture's own
            # qualitative signal rather than inventing a number (section 10).
            ratio = MIN_CONTRAST_RATIO * 0.7
            source = "qualitative_level"
        elif isinstance(contrast, (int, float)) and contrast < 0.6:
            # The pre-existing kiosk_standard fixture's plain 0-1 scale —
            # supported so this rule still works if pointed at that
            # environment, without duplicating its threshold logic.
            ratio = contrast * MIN_CONTRAST_RATIO
            source = "legacy_scale"

        if ratio is None or ratio >= MIN_CONTRAST_RATIO:
            return []

        shortfall = clamp((MIN_CONTRAST_RATIO - ratio) / MIN_CONTRAST_RATIO)
        # Any sub-threshold ratio is already a real, demonstrable barrier —
        # a floor of 0.5 rather than tapering to ~0 right at the threshold,
        # scaling toward 1.0 as the ratio falls further below it.
        severity = clamp(0.5 + 0.5 * shortfall)

        return [
            BarrierResult(
                barrier_type=self.barrier_type,
                ability_dimension=self.ability_dimension,
                severity=severity,
                confidence=vision.get("confidence", 0.5) if source == "computed" else min(vision.get("confidence", 0.5), 0.7),
                title="Low contrast text",
                description=(
                    f"Text contrast is below the WCAG-derived threshold ({MIN_CONTRAST_RATIO}:1) "
                    f"for a '{level}' vision profile."
                ),
                evidence={
                    "contrast_ratio": round(ratio, 2),
                    "threshold": MIN_CONTRAST_RATIO,
                    "source": source,
                    "ability_value": level,
                },
            )
        ]


class TooManyChoicesRule(BarrierRule):
    barrier_type = "too_many_choices"
    ability_dimension = "cognition"

    def detect(self, ability_profile, task, environment):
        cognition = _dimension(ability_profile, "cognition")
        level = cognition.get("level")
        if level not in COGNITION_TRIGGER_LEVELS:
            return []

        choice_count = environment.get("visible_choice_count")
        if choice_count is None:
            # No explicit environment fact — fall back to a real, known
            # quantity (how many controls the task itself exposes) rather
            # than inventing a number.
            choice_count = len(task.get("controls") or [])

        if choice_count <= MAX_SIMULTANEOUS_CHOICES:
            return []

        excess_ratio = clamp((choice_count - MAX_SIMULTANEOUS_CHOICES) / MAX_SIMULTANEOUS_CHOICES)
        base = COGNITION_BASE_SEVERITY.get(level, 0.5)
        severity = clamp(base + excess_ratio * (1 - base) * 0.6)

        return [
            BarrierResult(
                barrier_type=self.barrier_type,
                ability_dimension=self.ability_dimension,
                severity=severity,
                confidence=cognition.get("confidence", 0.5),
                title="Too many choices",
                description=(
                    f"{choice_count} simultaneous choices exceed the configured comfortable "
                    f"limit ({MAX_SIMULTANEOUS_CHOICES}) for a '{level}' cognition profile."
                ),
                evidence={
                    "choice_count": choice_count,
                    "threshold": MAX_SIMULTANEOUS_CHOICES,
                    "ability_value": level,
                },
            )
        ]


class AudioOnlyAlertRule(BarrierRule):
    barrier_type = "audio_only_alert"
    ability_dimension = "hearing"

    def detect(self, ability_profile, task, environment):
        hearing = _dimension(ability_profile, "hearing")
        level = hearing.get("level")
        if level not in HEARING_TRIGGER_LEVELS:
            return []

        alerts = environment.get("alerts") or task.get("alerts") or []
        critical_audio_only = [
            a for a in alerts if a.get("type") == "audio" and a.get("critical") and not a.get("has_visual_alternative")
        ]
        if not critical_audio_only:
            return []

        base = HEARING_BASE_SEVERITY.get(level, 0.6)
        severity = clamp(base)

        return [
            BarrierResult(
                barrier_type=self.barrier_type,
                ability_dimension=self.ability_dimension,
                severity=severity,
                confidence=hearing.get("confidence", 0.5),
                title="Audio-only alert",
                description=(
                    "Important information is presented only through audio, for a "
                    f"'{level}' hearing profile."
                ),
                evidence={
                    "alerts": critical_audio_only,
                    "ability_value": level,
                },
            )
        ]


BARRIER_RULES: list[BarrierRule] = [
    SmallTapTargetRule(),
    LowContrastTextRule(),
    TooManyChoicesRule(),
    AudioOnlyAlertRule(),
]

# fatigue_related_load (Phase 4 spec section 13) is deliberately NOT
# implemented: it requires a live fatigue *signal* distinct from the stored
# baseline profile (e.g. rising error rate during a session), and Phase 4
# has no such session-derived signal available to this standalone,
# session-independent engine. Implementing it against the static baseline
# profile alone would just be a restatement of the dexterity/cognition
# rules under a different name, not a real fatigue-tracking rule. Deferred
# until a real signal exists — see docs/PHASE_4.md.
