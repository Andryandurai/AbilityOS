"""Canonical predefined Ability Profile definitions (Phase 3).

The 9 named, user-facing profile concepts AbilityOS demonstrates -- kept
here as the single place their *trigger dimensions* (the ability values
that make a profile relevant) are defined, so
abilities.services.suggestion_service reads from exactly one source, not
an independently invented copy.

Relationship to backend/tasks/management/commands/seed_demo.py::
DEMO_PROFILES: that file seeds 9 full, working demo personas (all 10
dimensions, per-dimension confidence values, a username/password) for the
anonymous kiosk demo -- a different concern from this module, which only
describes "what combination of dimension values makes each named profile
concept relevant" for the suggestion engine. The trigger dimensions below
are kept in sync **by hand** with DEMO_PROFILES' own non-typical values
(the same "kept in sync by hand, documented, not by shared import" approach
already used for questionnaire seed data vs. the frontend's
ABILITY_QUESTIONS -- see docs/QUESTIONNAIRE.md). seed_demo.py was
deliberately left untouched rather than refactored to import from here:
Phase 3's instructions explicitly protect existing demo profile data from
accidental changes, and a refactor purely for DRY-ness would be exactly
the kind of unnecessary risk to that protected file this phase avoids.

Profile names/keys are presentation and grouping concepts only -- they are
never read by barrier detection, adaptation scoring, or any other part of
the AbilityOS reasoning core, which continues to operate purely on
AbilityProfile.dimensions.
"""

from __future__ import annotations

CANONICAL_PROFILES = [
    dict(
        key="low_vision_reduced_dexterity",
        name="Low Vision + Reduced Dexterity",
        description="Clearer visual presentation and larger, more forgiving touch targets.",
        dimensions={"vision": "large-text-needed", "dexterity": "reduced-precision"},
    ),
    dict(
        key="hearing_difficulty",
        name="Hearing Difficulty",
        description="Visual alternatives to audio-only information.",
        dimensions={"hearing": "relies-on-visual"},
    ),
    dict(
        key="cognitive_load",
        name="Cognitive Load",
        description="Fewer simultaneous choices and a clearer, more guided flow.",
        dimensions={"cognition": "needs-step-by-step", "fatigue": "moderate", "reaction_speed": "slower"},
    ),
    dict(
        key="limited_mobility_reach",
        name="Limited Mobility + Reach",
        description="Controls positioned within a comfortable reach zone.",
        dimensions={"reach": "seated", "mobility": "limited"},
    ),
    dict(
        key="speech_difficulty",
        name="Speech Difficulty",
        description="A reliable touch/text path wherever voice input is offered.",
        dimensions={"speech": "limited"},
    ),
    dict(
        key="fatigue_reduced_stamina",
        name="Fatigue / Reduced Stamina",
        description="Fewer repeated interactions and a lighter overall task flow.",
        dimensions={"fatigue": "high"},
    ),
    dict(
        key="slower_reaction_speed",
        name="Slower Reaction Speed",
        description="More time before a time-sensitive interaction expires.",
        dimensions={"reaction_speed": "slower"},
    ),
    dict(
        key="visual_hearing_support",
        name="Visual + Hearing Support",
        description="Higher contrast together with visual alternatives to audio.",
        dimensions={"vision": "low-contrast-sensitive", "hearing": "relies-on-visual"},
    ),
    dict(
        key="high_interaction_sensitivity",
        name="High Interaction Sensitivity",
        description="More clearly separated controls and deliberate confirmation before consequential actions.",
        dimensions={"interaction_sensitivity": "high"},
    ),
]

PROFILE_BY_KEY = {p["key"]: p for p in CANONICAL_PROFILES}
PROFILE_KEYS = [p["key"] for p in CANONICAL_PROFILES]
PROFILE_KEY_CHOICES = [(p["key"], p["name"]) for p in CANONICAL_PROFILES]
