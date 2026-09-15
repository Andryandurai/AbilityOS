"""Shared ownership check (Phase 2 section 23 / Phase 8 section 8).

Was previously duplicated verbatim in `abilities/views.py` and
`users/views.py`; centralized here so every endpoint that writes to a
specific user's data enforces the same rule, including the Phase 7
session/feedback endpoints that didn't have it at all.
"""

from __future__ import annotations

from rest_framework.exceptions import PermissionDenied


def assert_owner(request, owner_user_id, message="You may only access your own data.") -> None:
    """Any request carrying a real authenticated identity is held to real
    ownership rules. The anonymous hackathon-demo path (no login) is left
    open by design — see settings.py's REST_FRAMEWORK comment — but an
    authenticated caller may never act on another user's record unless
    they're staff."""

    requester = getattr(request, "user", None)
    if requester is not None and requester.is_authenticated:
        if not requester.is_staff and str(requester.id) != str(owner_user_id):
            raise PermissionDenied(message)
