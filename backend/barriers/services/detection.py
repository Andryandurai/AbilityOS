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
