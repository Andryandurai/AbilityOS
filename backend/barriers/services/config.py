"""Centralized Barrier Detection thresholds (Phase 4).

Every rule imports from here rather than hardcoding a number inline, so a
threshold only ever needs to change in one place.
"""

from __future__ import annotations

# --- Small tap targets ---------------------------------------------------------
# 160x48 is a commonly-cited "comfortable" touch target size for a person who
# doesn't have full precision (roughly 2x the platform-minimum ~44-48px a
# typical user manages fine) — deliberately more generous than a bare
# accessibility-guideline minimum, since AbilityOS is asking "comfortable for
# THIS profile", not "technically tappable at all".
MIN_TAP_TARGET_WIDTH = 160
MIN_TAP_TARGET_HEIGHT = 48

# A person whose dexterity profile indicates precise touch is difficult is
# the one this rule cares about; "typical" dexterity never triggers it — a
# small button is not inherently a barrier, only a mismatch with a specific
# profile (Phase 4 spec section 23).
DEXTERITY_TRIGGER_LEVELS = {"reduced-precision", "single-tap-only"}
# How severe the underlying limitation itself is, before factoring in how far
# below threshold the control actually is (see rules.py for the full formula).
DEXTERITY_BASE_SEVERITY = {"reduced-precision": 0.6, "single-tap-only": 0.85}

# --- Low contrast text ----------------------------------------------------------
# 4.5:1 is the WCAG 2.1 AA minimum contrast ratio for normal-size text —
# a well-established, externally-defined threshold rather than an invented
# number.
MIN_CONTRAST_RATIO = 4.5

VISION_CONTRAST_TRIGGER_LEVELS = {"low-contrast-sensitive"}

# --- Too many choices -------------------------------------------------------------
# Working-memory research commonly cites 4 as a comfortable number of
# simultaneously-held options for someone who finds many choices taxing;
# above that, AbilityOS treats the choice count itself as a fact worth
# flagging for a cognition-limited profile.
MAX_SIMULTANEOUS_CHOICES = 4

# needs-step-by-step implies at least as much difficulty with many
# simultaneous choices as prefers-fewer-choices does, so it is included too —
# not because the spec's illustrative example named it, but because excluding
# it would mean the more severe profile is treated as less affected than the
# milder one, which doesn't hold up.
COGNITION_TRIGGER_LEVELS = {"prefers-fewer-choices", "needs-step-by-step"}
COGNITION_BASE_SEVERITY = {"prefers-fewer-choices": 0.55, "needs-step-by-step": 0.75}

# --- Audio-only alerts -------------------------------------------------------------
HEARING_TRIGGER_LEVELS = {"partial", "relies-on-visual"}
HEARING_BASE_SEVERITY = {"partial": 0.55, "relies-on-visual": 0.8}

# --- Controls outside comfortable reach --------------------------------------------
# "full" reach never triggers this — a control's position is not inherently
# a barrier, only a mismatch with a specific profile (same principle as
# every other rule in this file).
REACH_TRIGGER_LEVELS = {"limited-upper", "seated"}
REACH_BASE_SEVERITY = {"limited-upper": 0.55, "seated": 0.8}

# --- Voice-only / speech-dependent interaction ---------------------------------------
# "typical" speech never triggers this — an environment offering a voice
# interaction is not inherently a barrier, only a mismatch with a profile
# that finds speech difficult or unreliable.
SPEECH_TRIGGER_LEVELS = {"limited", "unavailable"}
SPEECH_BASE_SEVERITY = {"limited": 0.55, "unavailable": 0.8}

# --- Excessive interaction burden -----------------------------------------------------
# "fresh" fatigue never triggers this — a multi-step flow is not inherently a
# barrier, only a mismatch with a profile for whom repeated navigation and
# re-selection add up over a task (a reduced-stamina profile), same principle
# as every other rule in this file.
FATIGUE_TRIGGER_LEVELS = {"moderate", "high"}
FATIGUE_BASE_SEVERITY = {"moderate": 0.35, "high": 0.7}
COMFORTABLE_INTERACTION_STEPS = 3

# --- Time-limited interaction -----------------------------------------------------
# "typical" never triggers this — REQUIRED_RESPONSE_SECONDS["typical"] equals
# the standard kiosk's own confirmation window (see fixtures), so a typical
# profile can never be below its own requirement by construction.
REACTION_TRIGGER_LEVELS = {"slower", "needs-extended-time"}
REACTION_BASE_SEVERITY = {"slower": 0.5, "needs-extended-time": 0.8}
REQUIRED_RESPONSE_SECONDS = {
    "typical": 5,
    "slower": 10,
    "needs-extended-time": 15,
}

# --- Accidental activation risk -----------------------------------------------------
# "typical" never triggers this -- tight spacing or a lack of confirmation is
# not inherently a barrier, only a mismatch with a profile that needs more
# deliberate, less accident-prone interaction.
INTERACTION_SENSITIVITY_TRIGGER_LEVELS = {"high"}
INTERACTION_SENSITIVITY_BASE_SEVERITY = {"high": 0.6}
SAFE_CONTROL_SEPARATION_PX = 32


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))
