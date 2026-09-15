"""Consent business logic (Phase 2 sections 2/15).

Consent gates *use* of a profile for adaptation, not the ability to view or
edit it — see `is_consented_for_adaptation`, which
`api.services.orchestrator.InteractionOrchestrator.start()` checks before
running anything against a person's profile.
"""

from __future__ import annotations

from django.utils import timezone

from users.models import ConsentRecord

DEFAULT_SCOPE = [ConsentRecord.SCOPE_INTERACTION_ADAPTATION]


def get_or_create_consent(user) -> ConsentRecord:
    record, _ = ConsentRecord.objects.get_or_create(user=user)
    return record


def grant_consent(user, scope: list | None = None) -> ConsentRecord:
    record = get_or_create_consent(user)
    record.granted = True
    record.scope = scope if scope is not None else DEFAULT_SCOPE
    record.granted_at = timezone.now()
    record.save()
    return record


def revoke_consent(user) -> ConsentRecord:
    record = get_or_create_consent(user)
    record.granted = False
    record.granted_at = None
    record.save()
    return record


def is_consented_for_adaptation(user) -> bool:
    """True only if consent is granted AND its scope explicitly covers
    interaction adaptation — the one thing AbilityOS actually needs
    permission for (Phase 2 section 2)."""

    record = get_or_create_consent(user)
    return bool(record.granted and ConsentRecord.SCOPE_INTERACTION_ADAPTATION in (record.scope or []))
