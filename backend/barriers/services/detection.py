"""Deterministic barrier detection (Part 3, Part 6 Module 5).

Compares an AbilityProfile against a TaskDescriptor and EnvironmentDescriptor
and lists the specific mismatches. This is intentionally rule-based —
"Do NOT use the LLM for basic deterministic barrier checks when a simple
rule is sufficient" — every barrier here is either present by threshold
comparison or it isn't; there is nothing for an LLM to reason about yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from barriers.models import Barrier

COMFORTABLE_TARGET_PX = 88  # ~48dp baseline scaled for a kiosk-distance display
COMFORTABLE_CONTRAST = 0.6
COMFORTABLE_CHOICE_COUNT = 4
# A flow of 3 or fewer distinct interaction steps/screens is comfortable even
# for a reduced-stamina profile; above that, each additional step is more
# navigation and re-selection over the course of the task.
COMFORTABLE_INTERACTION_STEPS = 3

DEXTERITY_SEVERITY = {
    "typical": 0.0,
    "reduced-precision": 0.65,
    "single-tap-only": 0.9,
}

VISION_SEVERITY = {
    "typical": 0.0,
    "low-contrast-sensitive": 0.6,
    "large-text-needed": 0.85,
}

COGNITION_SEVERITY = {
    "typical": 0.0,
    "prefers-fewer-choices": 0.55,
    "needs-step-by-step": 0.85,
}

HEARING_TRIGGERS = {"partial", "relies-on-visual"}

FATIGUE_SEVERITY = {
    "fresh": 0.0,
    "moderate": 0.35,
    "high": 0.7,
}

REACH_SEVERITY = {
    "full": 0.0,
    "limited-upper": 0.55,
    "seated": 0.8,
}

VOICE_SEVERITY = {
    "typical": 0.0,
    "limited": 0.6,
    "unavailable": 0.85,
}

REACTION_SEVERITY = {
    "typical": 0.0,
    "slower": 0.5,
    "needs-extended-time": 0.8,
}

# How many seconds a confirmation interaction must stay available for each
# reaction_speed level to be a comfortable, non-time-pressured response.
# "typical" is set equal to the standard kiosk's own confirmation window
# below, so a typical profile never triggers a mismatch by construction —
# same principle as every other severity dict in this file.
REQUIRED_RESPONSE_SECONDS = {
    "typical": 5,
    "slower": 10,
    "needs-extended-time": 15,
}

INTERACTION_SENSITIVITY_SEVERITY = {
    "typical": 0.0,
    "high": 0.6,
}

# A comfortable minimum gap between two adjacent interactive controls for a
# profile that needs more deliberate, less accident-prone interaction --
# distinct from COMFORTABLE_TARGET_PX (control SIZE); this is about the GAP
# between controls.
SAFE_CONTROL_SEPARATION_PX = 32


@dataclass
class DetectedBarrier:
    barrier_type: str
    ability_dimension: str
    severity: float
    confidence: float
    evidence: str

    def clamp(self) -> "DetectedBarrier":
        self.severity = max(0.0, min(1.0, round(self.severity, 3)))
        self.confidence = max(0.0, min(1.0, round(self.confidence, 3)))
        return self


def _dimension(profile_dimensions: dict, key: str) -> dict:
    return profile_dimensions.get(key, {"level": "typical", "confidence": 0.5, "source": "default"})


def _smallest_control_size(environment_data: dict) -> tuple[int, int] | None:
    controls = environment_data.get("controls") or []
    primary = [c for c in controls if c.get("primary", True)]
    pool = primary or controls
    if not pool:
        return None
    smallest = min(pool, key=lambda c: c.get("width", 999) * c.get("height", 999))
    return smallest.get("width", 999), smallest.get("height", 999)


def _primary_controls_outside_zone(environment_data: dict) -> list[dict] | None:
    """Returns the primary control(s) whose position falls outside the
    environment's configured `interaction_zone`, or None if either fact is
    missing from this environment (an environment with no positional data
    simply can't produce this barrier — not every environment needs to
    support every check)."""

    zone = environment_data.get("interaction_zone")
    controls = environment_data.get("controls") or []
    primary_controls = [c for c in controls if c.get("primary") and c.get("x") is not None and c.get("y") is not None]
    if not zone or not primary_controls:
        return None

    zx, zy = zone.get("x", 0), zone.get("y", 0)
    zw, zh = zone.get("width", 0), zone.get("height", 0)

    def outside(c):
        return not (zx <= c["x"] <= zx + zw and zy <= c["y"] <= zy + zh)

    return [c for c in primary_controls if outside(c)]


def _voice_only_controls(environment_data: dict) -> list[dict]:
    """Controls the environment itself declares as voice-interaction —
    a real environmental capability, present regardless of profile (same
    relationship `audio_alert` has to the `audio_only_alert` barrier: the
    kiosk fact exists either way, only certain profiles treat it as a
    mismatch)."""

    controls = environment_data.get("controls") or []
    return [c for c in controls if c.get("interaction_type") == "voice"]


def detect_barriers(profile_dimensions: dict, task_descriptor: dict, environment_data: dict) -> list[DetectedBarrier]:
    """Pure function: profile + task + environment -> list[DetectedBarrier].

    Kept side-effect free and independently testable; `detect_and_save`
    below is the persistence-aware wrapper used by the orchestrator.
    """

    barriers: list[DetectedBarrier] = []

    dexterity = _dimension(profile_dimensions, "dexterity")
    vision = _dimension(profile_dimensions, "vision")
    cognition = _dimension(profile_dimensions, "cognition")
    hearing = _dimension(profile_dimensions, "hearing")
    fatigue = _dimension(profile_dimensions, "fatigue")
    reach = _dimension(profile_dimensions, "reach")
    speech = _dimension(profile_dimensions, "speech")
    reaction_speed = _dimension(profile_dimensions, "reaction_speed")
    interaction_sensitivity = _dimension(profile_dimensions, "interaction_sensitivity")

    # 1. small_tap_targets
    size = _smallest_control_size(environment_data)
    dexterity_severity = DEXTERITY_SEVERITY.get(dexterity["level"], 0.0)
    if size and dexterity_severity > 0:
        width, height = size
        smallest_dim = min(width, height)
        if smallest_dim < COMFORTABLE_TARGET_PX:
            shortfall = (COMFORTABLE_TARGET_PX - smallest_dim) / COMFORTABLE_TARGET_PX
            severity = min(1.0, 0.4 + dexterity_severity * (0.5 + shortfall))
            barriers.append(
                DetectedBarrier(
                    barrier_type=Barrier.TYPE_SMALL_TAP_TARGETS,
                    ability_dimension="dexterity",
                    severity=severity,
                    confidence=dexterity.get("confidence", 0.5),
                    evidence=(
                        f"Primary control is {width}x{height}px, below the "
                        f"{COMFORTABLE_TARGET_PX}px comfortable target size for "
                        f"dexterity level '{dexterity['level']}'."
                    ),
                ).clamp()
            )

    # 2. low_contrast
    contrast = environment_data.get("contrast", 1.0)
    vision_severity = VISION_SEVERITY.get(vision["level"], 0.0)
    if vision_severity > 0 and contrast < COMFORTABLE_CONTRAST:
        deficit = (COMFORTABLE_CONTRAST - contrast) / COMFORTABLE_CONTRAST
        severity = min(1.0, 0.35 + vision_severity * (0.5 + deficit))
        barriers.append(
            DetectedBarrier(
                barrier_type=Barrier.TYPE_LOW_CONTRAST,
                ability_dimension="vision",
                severity=severity,
                confidence=vision.get("confidence", 0.5),
                evidence=(
                    f"Screen contrast ratio {contrast:.2f} is below the "
                    f"{COMFORTABLE_CONTRAST:.2f} comfortable threshold for vision "
                    f"level '{vision['level']}'."
                ),
            ).clamp()
        )

    # 3. too_many_choices
    choice_count = environment_data.get("visible_choice_count", 0)
    cognition_severity = COGNITION_SEVERITY.get(cognition["level"], 0.0)
    if cognition_severity > 0 and choice_count > COMFORTABLE_CHOICE_COUNT:
        excess = (choice_count - COMFORTABLE_CHOICE_COUNT) / COMFORTABLE_CHOICE_COUNT
        severity = min(1.0, 0.3 + cognition_severity * (0.5 + excess))
        barriers.append(
            DetectedBarrier(
                barrier_type=Barrier.TYPE_TOO_MANY_CHOICES,
                ability_dimension="cognition",
                severity=severity,
                confidence=cognition.get("confidence", 0.5),
                evidence=(
                    f"{choice_count} simultaneous choices exceed the "
                    f"{COMFORTABLE_CHOICE_COUNT}-choice comfortable limit for cognition "
                    f"level '{cognition['level']}'."
                ),
            ).clamp()
        )

    # 4. audio_only_alert
    audio_alert = environment_data.get("audio_alert", False)
    visual_mirror = environment_data.get("visual_alert_mirror", False)
    if audio_alert and not visual_mirror and hearing["level"] in HEARING_TRIGGERS:
        barriers.append(
            DetectedBarrier(
                barrier_type=Barrier.TYPE_AUDIO_ONLY_ALERT,
                ability_dimension="hearing",
                severity=0.8,
                confidence=hearing.get("confidence", 0.5),
                evidence=(
                    f"Task raises an audio-only alert with no visual/haptic mirror; "
                    f"hearing level is '{hearing['level']}'."
                ),
            ).clamp()
        )

    # 5. fatigue_degraded_precision (Workflow D): fatigue temporarily lowers
    # effective dexterity/cognition even for an otherwise-typical baseline.
    fatigue_severity = FATIGUE_SEVERITY.get(fatigue["level"], 0.0)
    if fatigue_severity > 0 and dexterity_severity == 0 and size:
        width, height = size
        if min(width, height) < COMFORTABLE_TARGET_PX * 1.1:
            barriers.append(
                DetectedBarrier(
                    barrier_type=Barrier.TYPE_FATIGUE_DEGRADED_PRECISION,
                    ability_dimension="fatigue",
                    severity=fatigue_severity,
                    confidence=fatigue.get("confidence", 0.5),
                    evidence=(
                        f"Session fatigue is '{fatigue['level']}'; effective "
                        f"precision/attention is temporarily reduced below baseline."
                    ),
                ).clamp()
            )

    # 6. controls_out_of_reach
    reach_severity = REACH_SEVERITY.get(reach["level"], 0.0)
    if reach_severity > 0:
        out_of_reach = _primary_controls_outside_zone(environment_data)
        if out_of_reach:
            control = out_of_reach[0]
            zone = environment_data["interaction_zone"]
            barriers.append(
                DetectedBarrier(
                    barrier_type=Barrier.TYPE_CONTROLS_OUT_OF_REACH,
                    ability_dimension="reach",
                    severity=reach_severity,
                    confidence=reach.get("confidence", 0.5),
                    evidence=(
                        f"Primary control '{control.get('id')}' is positioned at "
                        f"({control['x']}, {control['y']}), outside the configured comfortable "
                        f"interaction zone (x:{zone['x']}-{zone['x'] + zone['width']}, "
                        f"y:{zone['y']}-{zone['y'] + zone['height']}) for a '{reach['level']}' reach profile."
                    ),
                ).clamp()
            )

    # 7. voice_only_input
    speech_severity = VOICE_SEVERITY.get(speech["level"], 0.0)
    if speech_severity > 0:
        voice_controls = _voice_only_controls(environment_data)
        if voice_controls:
            control = voice_controls[0]
            barriers.append(
                DetectedBarrier(
                    barrier_type=Barrier.TYPE_VOICE_ONLY_INPUT,
                    ability_dimension="speech",
                    severity=speech_severity,
                    confidence=speech.get("confidence", 0.5),
                    evidence=(
                        f"The kiosk offers a voice-based interaction ('{control.get('label')}') for this "
                        f"task; speech-based interaction is required or suggested, while a '{speech['level']}' "
                        "speech profile prefers non-speech input."
                    ),
                ).clamp()
            )

    # 8. excessive_interaction_burden: distinct from fatigue_degraded_precision
    # (above) -- that rule is about temporarily reduced PRECISION on small
    # controls. This one is about the NUMBER of discrete interaction
    # steps/screens the current kiosk flow requires: repeated navigation and
    # re-selection is its own, separate burden, not a restatement of the
    # precision check under a different name.
    step_count = environment_data.get("interaction_step_count")
    if fatigue_severity > 0 and step_count is not None and step_count > COMFORTABLE_INTERACTION_STEPS:
        excess = (step_count - COMFORTABLE_INTERACTION_STEPS) / COMFORTABLE_INTERACTION_STEPS
        severity = min(1.0, 0.3 + fatigue_severity * (0.5 + excess))
        repeated_controls = [c for c in (environment_data.get("controls") or []) if c.get("repeated_action")]
        evidence = (
            f"This kiosk flow currently requires {step_count} interaction steps "
            f"(comfortable limit {COMFORTABLE_INTERACTION_STEPS}) for a '{fatigue['level']}' fatigue/stamina "
            "profile; repeated navigation and re-selection add up over the course of the task."
        )
        if repeated_controls:
            labels = ", ".join(c.get("label", c.get("id")) for c in repeated_controls)
            evidence += f" Includes repeated-tap controls: {labels}."
        barriers.append(
            DetectedBarrier(
                barrier_type=Barrier.TYPE_EXCESSIVE_INTERACTION_BURDEN,
                ability_dimension="fatigue",
                severity=severity,
                confidence=fatigue.get("confidence", 0.5),
                evidence=evidence,
            ).clamp()
        )

    # 9. time_limited_interaction: compares the profile's required response
    # window against the environment's actual confirmation window -- a
    # genuine PROFILE + ENVIRONMENT mismatch, never `if profile == X`. A
    # generous environment timeout (>= the profile's requirement) never
    # triggers this, no matter how slow the profile's reaction_speed is.
    reaction_severity = REACTION_SEVERITY.get(reaction_speed["level"], 0.0)
    actual_timeout = environment_data.get("confirmation_timeout_seconds")
    if reaction_severity > 0 and actual_timeout is not None:
        required = REQUIRED_RESPONSE_SECONDS.get(reaction_speed["level"], REQUIRED_RESPONSE_SECONDS["typical"])
        if actual_timeout < required:
            shortfall = (required - actual_timeout) / required
            severity = min(1.0, 0.3 + reaction_severity * (0.5 + shortfall))
            barriers.append(
                DetectedBarrier(
                    barrier_type=Barrier.TYPE_TIME_LIMITED_INTERACTION,
                    ability_dimension="reaction_speed",
                    severity=severity,
                    confidence=reaction_speed.get("confidence", 0.5),
                    evidence=(
                        f"The purchase confirmation provides only a {actual_timeout}-second response "
                        f"window, below the {required}-second response-time requirement configured for "
                        f"a '{reaction_speed['level']}' reaction-speed profile."
                    ),
                ).clamp()
            )

    # 10. accidental_activation_risk: compares this profile's need for more
    # deliberate, less accident-prone interaction against two independent
    # environment facts -- tight control spacing and/or a consequential
    # action offered with no confirmation step. Either fact alone is a
    # real, distinct mismatch (Section 7's "crowded controls" and
    # "destructive actions immediately activated"); both together simply
    # raise the severity. Never gated on profile identity -- a typical
    # profile never triggers this regardless of either fact.
    sensitivity_severity = INTERACTION_SENSITIVITY_SEVERITY.get(interaction_sensitivity["level"], 0.0)
    if sensitivity_severity > 0:
        spacing = environment_data.get("min_control_spacing_px")
        crowded = spacing is not None and spacing < SAFE_CONTROL_SEPARATION_PX
        unconfirmed = not environment_data.get("confirmation_available", False)
        if crowded or unconfirmed:
            causes = int(crowded) + int(unconfirmed)
            severity = min(1.0, sensitivity_severity + 0.15 * (causes - 1))
            reasons = []
            if crowded:
                reasons.append(
                    f"adjacent controls are only {spacing}px apart, below the "
                    f"{SAFE_CONTROL_SEPARATION_PX}px comfortable separation"
                )
            if unconfirmed:
                reasons.append("the consequential action (purchase) completes on a single tap with no confirmation step")
            evidence = (
                f"For a '{interaction_sensitivity['level']}' interaction-sensitivity profile, "
                + " and ".join(reasons)
                + "."
            )
            barriers.append(
                DetectedBarrier(
                    barrier_type=Barrier.TYPE_ACCIDENTAL_ACTIVATION_RISK,
                    ability_dimension="interaction_sensitivity",
                    severity=severity,
                    confidence=interaction_sensitivity.get("confidence", 0.5),
                    evidence=evidence,
                ).clamp()
            )

    barriers.sort(key=lambda b: b.severity, reverse=True)
    return barriers


def detect_and_save(session, profile, task, environment) -> list[Barrier]:
    """Runs detection and persists Barrier rows for the given session."""

    detected = detect_barriers(profile.dimensions, {"task_id": task.task_id}, environment.data)
    saved: list[Barrier] = []
    for d in detected:
        saved.append(
            Barrier.objects.create(
                session=session,
                barrier_type=d.barrier_type,
                ability_dimension=d.ability_dimension,
                severity=d.severity,
                confidence=d.confidence,
                evidence=d.evidence,
            )
        )
    return saved
