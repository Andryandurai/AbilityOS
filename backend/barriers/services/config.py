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


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))
