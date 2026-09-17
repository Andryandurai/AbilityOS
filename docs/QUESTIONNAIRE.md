# Functional Ability Questionnaire (Phase 2 — Onboarding, Consent & Questionnaire)

> **Scope note:** covers register→login (Phase 1, unchanged) through
> Welcome → Consent → Questionnaire → Generated Profile → Confirmation.
> Profile-suggestion cards (matching a person's answers to one of the 9
> demo personas) are **not** part of this phase — see "Deferred to Phase 3"
> below.

## 1. Purpose

A structured, guided way for a real, authenticated user to describe how
they prefer to interact with digital controls — one question at a time,
ending with a plain-language summary they explicitly confirm before
anything is saved.

## 2. Non-diagnostic design

The questionnaire never asks about a medical condition, diagnosis, or
disability. Every question asks about a functional interaction preference
("How comfortable are you reading small text?", "How precise is touch
interaction for you?") — the exact same 10 questions
`frontend/src/constants/abilityProfile.js::ABILITY_QUESTIONS` already asks
in the manual profile editor, just delivered one at a time with an
introduction and a review step. No question, option label, or generated
summary anywhere in this feature uses diagnostic language.

## 3. Existing dimensions (reused, not reinvented)

All 10 questions map directly to the 10 dimensions already defined in
`backend/abilities/constants.py::DIMENSION_KEYS`: `vision`, `hearing`,
`dexterity`, `reach`, `mobility`, `speech`, `cognition`, `fatigue`,
`reaction_speed`, `interaction_sensitivity`. No new dimension was
introduced. Every option's value is validated against
`ALLOWED_LEVELS[key]` — the same controlled vocabulary every other layer of
this codebase already reads from.

## 4. Question structure

One new Django app, `backend/questionnaire/`, with a single question type:
`single_choice` (no free text, multi-select, sliders, or scoring — Phase 2
section 7 explicitly ruled these out). Each `QuestionnaireQuestion` row
stores `key` (the ability dimension), `version`, `question_text`, `order`,
and `options` (a JSON list of `{value, label}`, where every `value` is one
of `ALLOWED_LEVELS[key]`).

**Kept in sync by hand, not by a shared file:** the Python seed data
(`questionnaire/management/commands/seed_questionnaire.py::QUESTIONS`)
mirrors `ABILITY_QUESTIONS` in the frontend exactly — same text, same
order, same option labels — because there's no practical way to share one
literal source across the Python/JS boundary without a build-time codegen
step, which was deliberately not added for this hackathon-scope phase (see
"Known limitations"). If a question's wording changes, both files need
updating.

## 5. Questionnaire versioning

`QuestionnaireQuestion.version` and `QuestionnaireSession.version` are
plain integers; there is no separate "QuestionnaireVersion" model (kept
minimal per Phase 2 section 7). The "current version" is simply the
highest version any question has been seeded at
(`questionnaire_service.current_version()`). A session captures its
version at `start_questionnaire()` and keeps it for its entire lifetime —
if the question set is ever re-seeded at version 2, an in-progress or
already-completed version-1 session is never silently reinterpreted
against the new set.

## 6. Response storage

`QuestionnaireResponse` — one row per `(session, question)`, enforced by a
`UniqueConstraint`. Answering the same question twice in one session
updates the existing row (`update_or_create`), it never creates a
duplicate. A response can only be written while its session is still
in-progress (`completed_at is None`) — once completed, the answers are
locked.

## 7. Response → dimension mapping

Deliberately the simplest possible mapping (Phase 2 section 11):

```
QuestionnaireQuestion.key  ──▶  dimensions dict key
QuestionnaireResponse.selected_value  ──▶  dimensions[key]["level"]
```

One question, one answer, one dimension — no scoring, no combining
multiple answers into one dimension, no AI. Every value is re-validated
against `ALLOWED_LEVELS` at the point the dimensions dict is built
(`build_dimensions_from_responses`), not just when it was first saved —
defense in depth against a stale or tampered row ever reaching
`AbilityProfile`.

## 8. Consent behavior

Reuses `users.ConsentRecord` exactly as-is — no new consent model or
scope. `POST /api/questionnaire/start/` checks
`users.services.consent_service.is_consented_for_adaptation(request.user)`
and rejects with 403 if consent hasn't been granted with the
`interaction_adaptation` scope. This is the one, early gate: since every
other questionnaire endpoint requires a `session_id` that can only exist
after a successful `start/` call, no response can ever be recorded without
consent already in place. Consent is never granted automatically —
registering an account does not imply consent (Phase 2 section 15).

## 9. Profile generation

`POST /api/questionnaire/{id}/complete/` validates every answer is present
and valid, builds the `dimensions` dict, and returns it —
**without writing to `AbilityProfile`.** The frontend shows this as a
review screen ("Here's what AbilityOS understands... Nothing has been
saved yet.") built from the exact same `summarizeProfile()` utility the
existing manual editor's summary page uses, so a questionnaire user and a
manual-editor user see their profile summarized identically.

## 10. Profile confirmation

**Why a separate confirm step exists:** Phase 2 section 14 requires that
answering questions must never itself change the person's real profile,
and section 21 explicitly asks for the safest clean architecture to be
identified rather than assumed. The chosen design: `complete/` locks in and
previews; a distinct `POST /api/questionnaire/{id}/confirm/` is the only
endpoint that writes anything, and it always re-derives `dimensions` fresh
from the session's stored responses (never from a client-supplied payload)
before calling **`abilities.services.profile_service.apply_manual_update()`
— the exact same function the manual profile editor already calls.** There
is no second write path into `AbilityProfile` anywhere in this feature; a
direct ORM write from questionnaire code was deliberately never introduced
(verified by a dedicated test —
`ProfileIntegrationTests.test_write_path_is_apply_manual_update_not_direct_orm`).

Abandoning the questionnaire at any point before confirming — including
after seeing the review screen — leaves the real `AbilityProfile`
completely untouched.

## 11. Security / ownership

Every questionnaire endpoint except `GET /api/questionnaire/` (public
reference data — question text, not personal information) requires
authentication. `QuestionnaireSession`/`QuestionnaireResponse` ownership is
enforced once, centrally, in `questionnaire/views.py::_owned_session()` —
mirroring `users/services/ownership.py::assert_owner()`'s owner-or-staff
rule already used throughout this codebase. Identity is always taken from
`request.user`, never from a client-supplied id. Verified end-to-end (both
automated tests and a live check): a second account can neither read,
answer, complete, nor confirm another user's session — every attempt
returns 403.

## 12. API endpoints

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/questionnaire/` | GET | No | Current question set (version + questions) |
| `/api/questionnaire/start/` | POST | Yes (+ consent) | Create a session for `request.user` |
| `/api/questionnaire/{id}/response/` | POST | Yes (owner) | Save/update one answer |
| `/api/questionnaire/{id}/complete/` | POST | Yes (owner) | Validate + generate `dimensions` (preview only) |
| `/api/questionnaire/{id}/confirm/` | POST | Yes (owner) | Write the generated `dimensions` via `apply_manual_update()` |

None of the existing endpoints changed shape. `GET /api/users/{id}/ability-
profile/` (unmodified) is exactly what returns a confirmed questionnaire's
result — proven live by fetching it immediately after `confirm/`.

## 13. Deferred to Phase 3

The following were **not** implemented in this phase:

- The 9 profile-suggestion cards (matching generated dimensions to one or
  more of the demo personas).
- Profile-suggestion matching logic.
- Profile selection / multi-profile confirmation
  (`UserProfileSelection`-equivalent).
- A personalized dashboard.
- A "retake questionnaire" UI (the data model already supports many
  `QuestionnaireSession` rows per user — `User → many QuestionnaireSessions`
  — but no frontend affordance to start a second one was built, per Phase 2
  section 37's explicit "do not build this yet").

## Known limitations

- Question text is duplicated by hand between
  `frontend/src/constants/abilityProfile.js` and
  `questionnaire/management/commands/seed_questionnaire.py` (see §4) — a
  true single source of truth across the Python/JS boundary would need a
  build-time codegen step, out of scope for this phase.
- The existing `JourneyIndicator` component (`select-user → consent →
  profile → summary`) is reused unmodified for the questionnaire path too
  — a questionnaire user sees "Profile" marked done at the Summary step
  even though they took the questionnaire, not the manual editor. Cosmetic
  only; fixing it would mean branching the indicator's step list by entry
  path, judged not worth the added complexity for this phase.
- `StartQuestionnaireView` reuses the existing `session_start` throttle
  scope rather than introducing a new one, for the same "create a new
  stateful session" reason that scope already protects
  `POST /api/interactions/start/`.
