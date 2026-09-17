# Profile Suggestions & User Profile Selection (Phase 3)

> **Scope note:** covers register→login→consent→questionnaire (Phases 1–2,
> unchanged) through Suggested Profiles → Selection → Confirmation → Task &
> Environment. A personalized dashboard is **not** part of this phase —
> see "Future extension possibilities."

## 1. Purpose

Once a real user has an `AbilityProfile` (from the Phase 2 questionnaire,
or the manual editor), Phase 3 compares its dimensions against 9 canonical,
named profile concepts and shows the person which ones look relevant —
with an honest, dimension-by-dimension explanation, never a confidence
score. The user decides what to do with each suggestion; nothing is ever
applied automatically.

## 2. Architecture

```
AbilityProfile.dimensions (existing, unchanged)
        │
        ▼
abilities.services.suggestion_service.suggest_profiles()   -- pure, deterministic, no DB writes
        │
        ▼
GET /api/users/{id}/profile-suggestions/                    -- read-only
        │
        ▼
User reviews (SuggestedProfilesPage.jsx)
        │
        ▼
POST /api/users/{id}/profile-selections/                    -- the ONLY write in this feature
        │
        ▼
UserProfileSelection (new model, abilities app)
```

**`AbilityProfile.dimensions` remains the sole source of reasoning.**
Profile names ("Low Vision + Reduced Dexterity") are presentation/grouping
labels only — `UserProfileSelection` rows are never read by barrier
detection, adaptation scoring, or any other part of the AbilityOS
reasoning core, which continues to operate purely on the dimensions dict
it always has.

## 3. Profile definitions

Canonical trigger dimensions for all 9 profiles live in one place,
`backend/abilities/profiles.py::CANONICAL_PROFILES` — extracted so the
suggestion engine has a single source, rather than an independently
invented copy. Every trigger dimension key/value is validated by a
dedicated test (`CanonicalProfileDataTests`) against
`abilities.constants.DIMENSION_KEYS`/`ALLOWED_LEVELS`.

**Relationship to `seed_demo.py::DEMO_PROFILES`:** that file seeds 9 full
working demo personas for the anonymous kiosk demo — a different concern.
`abilities/profiles.py`'s trigger dimensions are kept in sync **by hand**
with `DEMO_PROFILES`' own non-typical values (documented in the module's
own docstring), the same approach already used for the Phase 2
questionnaire's seed data vs. the frontend's `ABILITY_QUESTIONS`.
`seed_demo.py` itself was **not** modified — refactoring it to import from
here was considered and rejected, since it would risk changing the
protected, already-seeded demo profile data for no functional benefit.

## 4. Matching logic

Deterministic, explainable, no AI:

```python
for profile in CANONICAL_PROFILES:
    matched = [dim for dim, required in profile["dimensions"].items()
               if user_dimensions.get(dim, {}).get("level") == required]
    if matched:
        suggest(profile, matched_dimensions=matched, match_count=len(matched),
                full_match=len(matched) == len(profile["dimensions"]))
```

A **partial** match (at least one, but not all, of a profile's trigger
dimensions) is still surfaced — e.g. a person with only
`hearing: relies-on-visual` sees both "Hearing Difficulty" (full match) and
"Visual + Hearing Support" (partial match, 1 of 2) — because a partial
match is real, explainable information, not noise to hide (verified by
`test_partial_match_is_explainable_not_hidden`). Suggestions are sorted by
`match_count` descending. A profile with zero matching dimensions is
omitted from `suggestions` entirely; `all_profiles` (also returned by the
same endpoint) is the complete, unfiltered list of all 9, used to populate
the "manually add a profile" picker.

## 5. User selection lifecycle

`UserProfileSelection` — one row per `(user, profile_key)`, unique
constraint enforced at the DB level. Four statuses
(`suggested`/`accepted`/`rejected`/`manually_added`), Django `choices`
only — an arbitrary status string is rejected by the serializer before it
reaches the service layer. A user may hold any number of `accepted`
selections simultaneously (never single-select). Rejecting a suggestion
**keeps** the row (`status=rejected`) rather than deleting it — deletion is
a distinct, explicit action (`DELETE .../profile-selections/{key}/`),
verified by `test_rejecting_does_not_delete_the_row`.

The `suggested` status is available in the schema for completeness but is
never written automatically by `GET .../profile-suggestions/` — that
endpoint is pure and side-effect-free (verified by
`test_viewing_suggestions_does_not_create_selection_rows`). A row only ever
exists once the user takes an explicit action (accept/reject/manually add).

## 6. API endpoints

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/users/{id}/profile-suggestions/` | GET | Owner (or staff) | Computed suggestions + the full 9-profile catalogue |
| `/api/users/{id}/profile-selections/` | GET | Owner (or staff) | The user's current selections |
| `/api/users/{id}/profile-selections/` | POST | Owner (or staff) | Create/update one selection (upsert) |
| `/api/users/{id}/profile-selections/{profile_key}/` | DELETE | Owner (or staff) | Remove one selection entirely |

All four require authentication (`IsAuthenticated`) — unlike
`AbilityProfileView`/`ConsentView`, which stay anonymous-compatible for the
pre-existing demo flow, nothing in the real onboarding journey these
endpoints serve ever needs anonymous access, so there's no legacy
behaviour to preserve.

## 7. Security / ownership

Every endpoint calls the existing `users.services.ownership.assert_owner()`
— the same owner-or-staff helper `AbilityProfileView`/`ConsentView`/every
`/api/interactions/...` endpoint already uses. Identity is always the
authenticated `request.user`; a client-supplied user id in the URL is only
ever used after ownership is confirmed. Verified live and via 6 dedicated
tests (`ProfileSelectionOwnershipTests`): a second account gets 403
reading suggestions, reading selections, creating a selection, modifying a
selection, or deleting a selection for another user; an unauthenticated
request gets 401.

## 8. Profile mutation rules

**Suggestions never automatically modify the AbilityProfile.** Neither
does accepting, rejecting, nor manually adding a profile — every one of
those actions only ever creates/updates a `UserProfileSelection` row.
`abilities/services/selection_service.py` never imports or calls
`apply_manual_update()` (or any other `AbilityProfile` write path); a
dedicated regression test on both the suggestions endpoint and the
selections endpoint asserts the profile's `dimensions` dict is
byte-for-byte identical before and after.

If a future phase wants a selected profile's dimensions to actually be
written onto the real `AbilityProfile`, that must go through the existing
`abilities.services.profile_service.apply_manual_update()` — the same
single write path the manual editor and the Phase 2 questionnaire's
confirm step already use. Phase 3 does not add a second one.

## 9. Multi-profile behaviour

Multiple profiles can be selected simultaneously with no special
conflict resolution. If two accepted profiles express different values
for the same dimension (e.g. one profile's `vision: large-text-needed` vs.
another's `vision: low-contrast-sensitive`), nothing in Phase 3 resolves
that — because nothing in Phase 3 ever writes a selected profile's
dimensions onto `AbilityProfile` at all (see §8). The existing
`AbilityProfile.dimensions` values (from the questionnaire or manual
editor) are always preserved untouched; profile selections are a purely
separate, descriptive record of the person's own stance on named concepts.

## 10. Known limitations

- No caching/audit model for *suggestions themselves* (`ProfileSuggestion`)
  — they're recomputed on every GET, which is cheap (9 profiles × ~10
  dimensions, no extra queries beyond the profile itself) and avoids an
  unnecessary table, per Phase 3's own "do not add an unnecessary database
  model" guidance.
- No UI/API path yet applies a selected profile's dimensions onto the real
  `AbilityProfile` — selections are currently a standalone record of the
  user's stance, not (yet) a second way to edit the profile. See §8/§11.
- `abilities/profiles.py`'s trigger dimensions are kept in sync with
  `seed_demo.py::DEMO_PROFILES` by hand, not by shared import (§3).

## 11. Future extension possibilities

- A personalized dashboard surfacing the user's `accepted` selections.
- An explicit "apply this profile's dimensions to my Ability Profile"
  action, routed through the existing `apply_manual_update()` — with a
  defined conflict-resolution rule if more than one accepted profile
  disagrees on a dimension (deliberately out of scope for Phase 3, per
  §15 of the Phase 3 brief).
- Persisting a `ProfileSuggestion` audit row if a future need for "what
  was suggested and when" (beyond what's recomputable live) emerges.
