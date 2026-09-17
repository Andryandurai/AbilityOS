"""User profile selection business logic (Phase 3).

Kept separate from profile_service.py (which owns AbilityProfile writes)
-- this module only ever touches UserProfileSelection rows. Nothing here
calls apply_manual_update() or writes to AbilityProfile.dimensions in any
way; selecting a profile records the person's own stance on a named
concept, it does not by itself change what AbilityOS reasons about (Phase
3 section 14 -- see docs/PROFILE_SUGGESTIONS.md for the full rule).
"""

from __future__ import annotations

from abilities.models import UserProfileSelection


def list_selections(user):
    return UserProfileSelection.objects.filter(user=user)


def upsert_selection(user, profile_key: str, status: str) -> UserProfileSelection:
    """Create or update the one selection row for (user, profile_key) --
    the model's own UniqueConstraint is what actually prevents duplicates;
    this just makes "create or update" atomic and explicit rather than a
    get-then-branch race."""

    selection, _ = UserProfileSelection.objects.update_or_create(
        user=user, profile_key=profile_key, defaults={"status": status}
    )
    return selection


def delete_selection(user, profile_key: str) -> bool:
    """Returns True if a row was actually deleted, False if there was
    nothing to delete for this (user, profile_key) -- lets the view decide
    whether that's a 204 or a 404 without needing a second query."""

    deleted_count, _ = UserProfileSelection.objects.filter(user=user, profile_key=profile_key).delete()
    return deleted_count > 0
