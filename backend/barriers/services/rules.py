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
    COMFORTABLE_INTERACTION_STEPS,
    DEXTERITY_BASE_SEVERITY,
    DEXTERITY_TRIGGER_LEVELS,
    FATIGUE_BASE_SEVERITY,
    FATIGUE_TRIGGER_LEVELS,
    HEARING_BASE_SEVERITY,
    HEARING_TRIGGER_LEVELS,
    INTERACTION_SENSITIVITY_BASE_SEVERITY,
    INTERACTION_SENSITIVITY_TRIGGER_LEVELS,
    MAX_SIMULTANEOUS_CHOICES,
    MIN_CONTRAST_RATIO,
    MIN_TAP_TARGET_HEIGHT,
    MIN_TAP_TARGET_WIDTH,
    REACH_BASE_SEVERITY,
    REACH_TRIGGER_LEVELS,
    REACTION_BASE_SEVERITY,
    REACTION_TRIGGER_LEVELS,
    REQUIRED_RESPONSE_SECONDS,
    SAFE_CONTROL_SEPARATION_PX,
    SPEECH_BASE_SEVERITY,
    SPEECH_TRIGGER_LEVELS,
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


class ControlsOutOfReachRule(BarrierRule):
    barrier_type = "controls_out_of_reach"
    ability_dimension = "reach"

    def detect(self, ability_profile, task, environment):
        reach = _dimension(ability_profile, "reach")
        level = reach.get("level")
        if level not in REACH_TRIGGER_LEVELS:
            return []

        zone = environment.get("interaction_zone")
        if not zone:
            return []

        controls = _task_relevant_controls(task, environment)
        positioned = [c for c in controls if c.get("x") is not None and c.get("y") is not None]
        if not positioned:
            return []

        zx, zy = zone.get("x", 0), zone.get("y", 0)
        zw, zh = zone.get("width", 0), zone.get("height", 0)

        def outside(c):
            return not (zx <= c["x"] <= zx + zw and zy <= c["y"] <= zy + zh)

        out_of_reach = [c for c in positioned if outside(c)]
        if not out_of_reach:
            return []

        base = REACH_BASE_SEVERITY.get(level, 0.5)
        severity = clamp(base)

        return [
            BarrierResult(
                barrier_type=self.barrier_type,
                ability_dimension=self.ability_dimension,
                severity=severity,
                confidence=reach.get("confidence", 0.5),
                title="Controls outside comfortable reach",
                description=(
                    "One or more interaction controls are positioned outside the configured "
                    f"comfortable interaction zone for a '{level}' reach profile."
                ),
                evidence={
                    "controls": [{"id": c.get("id"), "x": c.get("x"), "y": c.get("y")} for c in out_of_reach],
                    "interaction_zone": zone,
                    "ability_value": level,
                },
            )
        ]


class VoiceOnlyInputRule(BarrierRule):
    barrier_type = "voice_only_input"
    ability_dimension = "speech"

    def detect(self, ability_profile, task, environment):
        speech = _dimension(ability_profile, "speech")
        level = speech.get("level")
        if level not in SPEECH_TRIGGER_LEVELS:
            return []

        controls = environment.get("controls") or []
        voice_controls = [c for c in controls if c.get("interaction_type") == "voice"]
        if not voice_controls:
            return []

        base = SPEECH_BASE_SEVERITY.get(level, 0.5)
        severity = clamp(base)
        control = voice_controls[0]

        return [
            BarrierResult(
                barrier_type=self.barrier_type,
                ability_dimension=self.ability_dimension,
                severity=severity,
                confidence=speech.get("confidence", 0.5),
                title="Voice-only / speech-dependent interaction",
                description=(
                    "Speech-based interaction is offered or required for this interaction, while the "
                    f"selected profile prefers non-speech input, for a '{level}' speech profile."
                ),
                evidence={
                    "controls": [{"id": c.get("id"), "label": c.get("label")} for c in voice_controls],
                    "ability_value": level,
                },
            )
        ]


class ExcessiveInteractionBurdenRule(BarrierRule):
    barrier_type = "excessive_interaction_burden"
    ability_dimension = "fatigue"

    def detect(self, ability_profile, task, environment):
        fatigue = _dimension(ability_profile, "fatigue")
        level = fatigue.get("level")
        if level not in FATIGUE_TRIGGER_LEVELS:
            return []

        step_count = environment.get("interaction_step_count")
        if step_count is None:
            # No explicit environment fact — fall back to the task's own
            # real step count rather than inventing a number (same
            # fallback shape TooManyChoicesRule uses above).
            step_count = len(task.get("steps") or [])
        if not step_count or step_count <= COMFORTABLE_INTERACTION_STEPS:
            return []

        excess_ratio = clamp((step_count - COMFORTABLE_INTERACTION_STEPS) / COMFORTABLE_INTERACTION_STEPS)
        base = FATIGUE_BASE_SEVERITY.get(level, 0.5)
        severity = clamp(base + excess_ratio * (1 - base) * 0.6)

        controls = _task_relevant_controls(task, environment)
        repeated_controls = [c for c in controls if c.get("repeated_action")]

        return [
            BarrierResult(
                barrier_type=self.barrier_type,
                ability_dimension=self.ability_dimension,
                severity=severity,
                confidence=fatigue.get("confidence", 0.5),
                title="Excessive interaction burden",
                description=(
                    f"This task currently requires {step_count} interaction steps/screens "
                    f"(comfortable limit {COMFORTABLE_INTERACTION_STEPS}), adding navigation "
                    f"transitions and repeated interactions for a '{level}' fatigue/stamina profile."
                ),
                evidence={
                    "step_count": step_count,
                    "threshold": COMFORTABLE_INTERACTION_STEPS,
                    "repeated_action_controls": [
                        {"id": c.get("id"), "label": c.get("label")} for c in repeated_controls
                    ],
                    "ability_value": level,
                },
            )
        ]


class TimeLimitedInteractionRule(BarrierRule):
    barrier_type = "time_limited_interaction"
    ability_dimension = "reaction_speed"

    def detect(self, ability_profile, task, environment):
        reaction_speed = _dimension(ability_profile, "reaction_speed")
        level = reaction_speed.get("level")
        if level not in REACTION_TRIGGER_LEVELS:
            return []

        actual_timeout = environment.get("confirmation_timeout_seconds")
        if actual_timeout is None:
            return []

        required = REQUIRED_RESPONSE_SECONDS.get(level, REQUIRED_RESPONSE_SECONDS["typical"])
        if actual_timeout >= required:
            return []

        shortfall = clamp((required - actual_timeout) / required)
        base = REACTION_BASE_SEVERITY.get(level, 0.5)
        severity = clamp(base + shortfall * (1 - base) * 0.6)

        return [
            BarrierResult(
                barrier_type=self.barrier_type,
                ability_dimension=self.ability_dimension,
                severity=severity,
                confidence=reaction_speed.get("confidence", 0.5),
                title="Time-limited interaction",
                description=(
                    f"The confirmation interaction allows only {actual_timeout} seconds for a response, "
                    f"below the {required}-second response-time requirement for a '{level}' reaction-speed "
                    "profile."
                ),
                evidence={
                    "actual_timeout_seconds": actual_timeout,
                    "required_seconds": required,
                    "ability_value": level,
                },
            )
        ]


class AccidentalActivationRiskRule(BarrierRule):
    barrier_type = "accidental_activation_risk"
    ability_dimension = "interaction_sensitivity"

    def detect(self, ability_profile, task, environment):
        sensitivity = _dimension(ability_profile, "interaction_sensitivity")
        level = sensitivity.get("level")
        if level not in INTERACTION_SENSITIVITY_TRIGGER_LEVELS:
            return []

        spacing = environment.get("min_control_spacing_px")
        crowded = spacing is not None and spacing < SAFE_CONTROL_SEPARATION_PX
        unconfirmed = not environment.get("confirmation_available", False)
        if not crowded and not unconfirmed:
            return []

        causes = int(crowded) + int(unconfirmed)
        base = INTERACTION_SENSITIVITY_BASE_SEVERITY.get(level, 0.5)
        severity = clamp(base + 0.15 * (causes - 1))

        reasons = []
        if crowded:
            reasons.append(
                f"adjacent controls are only {spacing}px apart, below the "
                f"{SAFE_CONTROL_SEPARATION_PX}px comfortable separation"
            )
        if unconfirmed:
            reasons.append("the consequential action completes on a single tap with no confirmation step")

        return [
            BarrierResult(
                barrier_type=self.barrier_type,
                ability_dimension=self.ability_dimension,
                severity=severity,
                confidence=sensitivity.get("confidence", 0.5),
                title="Accidental activation risk",
                description=(
                    f"This interaction is more likely to result in an accidental or unintended action than "
                    f"is comfortable for a '{level}' interaction-sensitivity profile: " + " and ".join(reasons) + "."
                ),
                evidence={
                    "min_control_spacing_px": spacing,
                    "safe_separation_px": SAFE_CONTROL_SEPARATION_PX,
                    "confirmation_available": environment.get("confirmation_available", False),
                    "ability_value": level,
                },
            )
        ]


BARRIER_RULES: list[BarrierRule] = [
    SmallTapTargetRule(),
    LowContrastTextRule(),
    TooManyChoicesRule(),
    AudioOnlyAlertRule(),
    ControlsOutOfReachRule(),
    VoiceOnlyInputRule(),
    ExcessiveInteractionBurdenRule(),
    TimeLimitedInteractionRule(),
    AccidentalActivationRiskRule(),
]

# fatigue_related_load (Phase 4 spec section 13) is still deliberately NOT
# implemented: it would need a live fatigue *signal* distinct from the
# stored baseline profile (e.g. rising error rate during a session), which
# this standalone, session-independent engine has no access to. That is a
# different concept from ExcessiveInteractionBurdenRule above:
# fatigue_related_load would restate dexterity/cognition against the same
# static baseline under a different name, whereas
# ExcessiveInteractionBurdenRule checks a fact neither of those rules
# looks at (how many discrete interaction steps the flow requires) — a
# genuine, separate mismatch, not a forced reuse. fatigue_related_load
# itself stays deferred until a real session-derived signal exists — see
# docs/PHASE_4.md.
