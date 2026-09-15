"""Single source of truth for the controlled Ability Profile vocabulary.

Every layer (Django model defaults, DRF validation, service-layer guards,
seed data, tests) imports from here instead of hardcoding strings, so the
"same spelling in every layer" requirement holds by construction rather
than by convention.
"""

from __future__ import annotations

DIMENSION_KEYS = [
    "vision",
    "hearing",
    "dexterity",
    "reach",
    "mobility",
    "speech",
    "cognition",
    "fatigue",
    "reaction_speed",
]

# Controlled values per dimension — never arbitrary free text (Phase 2 spec
# section 4). The first entry in each list is that dimension's "no barrier"
# baseline, used by DEFAULT_LEVEL below.
ALLOWED_LEVELS = {
    "vision": ["typical", "low-contrast-sensitive", "large-text-needed"],
    "hearing": ["typical", "partial", "relies-on-visual"],
    "dexterity": ["typical", "reduced-precision", "single-tap-only"],
    "reach": ["full", "limited-upper", "seated"],
    "mobility": ["typical", "limited", "stationary"],
    "speech": ["typical", "limited", "unavailable"],
    "cognition": ["typical", "prefers-fewer-choices", "needs-step-by-step"],
    "fatigue": ["fresh", "moderate", "high"],
    "reaction_speed": ["typical", "slower", "needs-extended-time"],
}

DEFAULT_LEVEL = {key: values[0] for key, values in ALLOWED_LEVELS.items()}

MODALITY_VALUES = ["visual", "voice", "haptic", "mixed"]

SOURCE_MANUAL = "manual"
SOURCE_INFERRED = "inferred"
SOURCE_DEFAULT = "default"
SOURCE_SESSION_SIGNAL = "session_signal"

ALLOWED_SOURCES = [SOURCE_MANUAL, SOURCE_INFERRED, SOURCE_DEFAULT, SOURCE_SESSION_SIGNAL]

# "Manual beats inferred beats default" (Phase 2 spec section 7). Used by
# abilities.services.profile_service to decide whether an incoming write is
# allowed to overwrite what's already stored. session_signal is treated as
# the same trust tier as inferred — both are system-observed, not
# hand-entered, and both must yield to an existing manual value.
SOURCE_PRIORITY = {
    SOURCE_MANUAL: 3,
    SOURCE_INFERRED: 2,
    SOURCE_SESSION_SIGNAL: 2,
    SOURCE_DEFAULT: 1,
}
