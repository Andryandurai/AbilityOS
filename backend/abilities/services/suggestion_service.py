"""Deterministic profile suggestion logic (Phase 3).

Compares a real AbilityProfile's dimensions against the canonical profile
definitions in abilities.profiles and returns which ones are relevant, and
why. No AI, no ML, no scoring beyond a plain count of matching dimensions
-- explainable by construction: every suggestion carries the exact
dimension keys that caused it.

This module never writes anything -- it is pure computation over already-
validated data, mirroring barriers.services.detection's "pure function,
side-effect free" shape in this codebase. Nothing here mutates
AbilityProfile; only abilities.services.profile_service.apply_manual_update()
(called elsewhere, never from here) is ever allowed to do that.
"""

from __future__ import annotations

from abilities.profiles import CANONICAL_PROFILES, PROFILE_BY_KEY


def suggest_profiles(profile_dimensions: dict) -> list[dict]:
    """Returns one entry per canonical profile with at least one matching
    dimension, ranked by how many of that profile's trigger dimensions
    match (most-relevant first) -- a partial match is real, explainable
    information (Phase 3 section 8: "explainable, not prediction"), not
    noise to filter out. A profile with zero matching dimensions is
    omitted entirely; use list_all_profiles() for the complete, unfiltered
    catalogue (e.g. for a "manually add a profile" picker)."""

    suggestions = []
    for profile in CANONICAL_PROFILES:
        matched_dimensions = [
            dim_key
            for dim_key, required_level in profile["dimensions"].items()
            if profile_dimensions.get(dim_key, {}).get("level") == required_level
        ]
        if not matched_dimensions:
            continue
        suggestions.append(
            {
                "profile_key": profile["key"],
                "name": profile["name"],
                "description": profile["description"],
                "matched_dimensions": matched_dimensions,
                "match_count": len(matched_dimensions),
                "full_match": len(matched_dimensions) == len(profile["dimensions"]),
            }
        )

    suggestions.sort(key=lambda s: s["match_count"], reverse=True)
    return suggestions


def list_all_profiles() -> list[dict]:
    """The complete, unfiltered canonical catalogue -- e.g. for a
    "manually add a profile that wasn't suggested" picker, which must be
    able to show all 9 regardless of the current profile's dimensions."""

    return [
        {"profile_key": p["key"], "name": p["name"], "description": p["description"]} for p in CANONICAL_PROFILES
    ]


def is_valid_profile_key(profile_key: str) -> bool:
    return profile_key in PROFILE_BY_KEY
