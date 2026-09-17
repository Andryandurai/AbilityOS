# Personalized Dashboard (Phase 4)

> **Scope note:** covers register→login→consent→questionnaire (Phases 1–2)
> through Suggested Profiles → Selection → Confirmation (Phase 3) →
> Dashboard, and Dashboard's "Start Experience" hand-off into the existing
> Task & Environment → Kiosk flow. Nothing about that downstream flow
> itself changed — see "What was deferred."

## 1. Purpose

Give a logged-in user a single home screen: what AbilityOS currently
understands about them, which named profiles they've selected, and one
clear way in to actually experience an adapted task. It replaces "jump
straight into onboarding" as the account entry point with "land on your
own page, and start (or continue) onboarding from there if you haven't
yet."

## 2. Architecture

```
GET /api/auth/me/                         -- already loaded (useAuth)
GET /api/users/{id}/ability-profile/      -- already loaded (useProfileFlow, awaited
                                              before Dashboard ever renders)
        │
        ▼
DashboardPage.jsx (new) -- reads `user`/`profile` as props, no re-fetch
        │
        ▼
GET /api/users/{id}/profile-suggestions/  -- read-only, reused from Phase 3
GET /api/users/{id}/profile-selections/   -- read-only, reused from Phase 3
```

No new backend model, serializer, view, or URL was added. The Dashboard
is composed entirely from three existing, already-authenticated endpoints
(Phase 1's `/auth/me/`, Phase 2/0's `/ability-profile/`, Phase 3's
`/profile-suggestions/` + `/profile-selections/`), consistent with the
"no `/api/dashboard/`endpoint unless genuinely required" guidance — nothing
about "welcome + profile summary + selected profiles + an entry point"
needs data no existing endpoint already returns.

**Why `profile` is a prop, not a fetch:** `App.jsx`'s `handleGoToDashboard`
already `await`s `useProfileFlow`'s `selectUser(auth.user.id)` — which
fetches the Ability Profile and consent record — before ever setting
`stage` to `"dashboard"`. Re-fetching it inside `DashboardPage` would risk
a second, momentarily-inconsistent copy for no benefit; the page trusts
the same single source of truth every other profile-flow screen
(`ProfileSummaryPage`, `AbilityProfileEditorPage`) already uses.

**Why suggestions/selections *are* fetched here:** `GET
.../profile-selections/` intentionally has no `name`/`description` field
of its own (see `docs/PROFILE_SUGGESTIONS.md` §6) — `all_profiles` from
the suggestions endpoint is the one place a `profile_key` resolves to a
human-readable name. `SuggestedProfilesPage.jsx` already fetches this
exact pair for the same reason; the Dashboard reuses the pattern rather
than adding a backend field to avoid it.

## 3. Entry point change

Before Phase 4, the authenticated Landing Page button ("Continue to your
Ability Profile") skipped straight into Consent → Questionnaire every
time. It's now "Go to my Dashboard" (`onGoToDashboard` /
`handleGoToDashboard`), and always lands on the Dashboard first:

- **First-ever visit** (no dimension has moved off its baseline level
  yet): the Ability Profile card shows an explicit empty state and a
  "Set up your Ability Profile" button, which is the *only* thing that
  still starts the existing Welcome → Consent → Questionnaire → Profile
  Summary chain (`handleSetupProfile` → `setStage("welcome")`, unchanged
  from Phase 2).
- **Every subsequent visit** (including a fresh login on another day):
  the same button/CTA lands directly on the populated Dashboard — no
  forced re-onboarding detour.

First-time setup itself now ends back at the Dashboard instead of Task &
Environment: `SuggestedProfilesPage`'s "Confirm & Continue"
(`handleSuggestedProfilesComplete`) sets `stage` to `"dashboard"`, not
`"task-environment"`. "Start Experience" on the Dashboard
(`handleStartExperienceFromDashboard`) is the new, explicit entry point
into that flow.

## 4. "Have they set up a profile yet?" — the modality quirk

`summarizeProfile()` (Phase 2, `constants/abilityProfile.js`) was already
being used as an implicit "is this profile non-trivial" signal elsewhere
(`ProfileSummaryPage`'s "typical across the board" empty state), but it
can never actually return an empty array: `AbilityProfile.preferred_modality`
defaults to `"visual"` (`abilities/services/profile_service.py`'s
`clear_profile`/creation defaults), and `summarizeProfile()`
unconditionally appends a `MODALITY_COPY` entry for whatever
`preferred_modality` is set to, regardless of whether it's still at its
default. A dimension only ever contributes an entry once it's moved off
its own default level; modality is never "empty" the same way.

Rather than touch that existing behaviour (used elsewhere, out of this
phase's scope), a small dedicated export was added:
`hasCustomizedDimensions(profile)` — true only if at least one *dimension*
has a `SUMMARY_COPY` entry for its current level, deliberately ignoring
`preferred_modality`. The Dashboard uses this (not
`summarizeProfile(...).length`) to decide which button/empty-state to
show. `summarizeProfile()` itself, and every other page that calls it,
is unchanged.

## 5. Selected Profiles

Reuses the same "selected" definition Phase 3 established:
`status` is `accepted` or `manually_added`. `suggested`/`rejected` rows,
and any profile with no row at all, are not shown. The section's own
empty state ("You haven't selected any profiles yet.") and its "Manage
Profiles" button (→ `SuggestedProfilesPage`, unchanged component) are
both always available regardless of Ability Profile completeness — a
person can browse and select named profiles before ever touching the
questionnaire, exactly as Phase 3 already allowed.

`SuggestedProfilesPage`'s "Back" button is now reachable from two call
sites (the first-time flow, coming from Profile Summary; and Dashboard's
"Manage Profiles", any time after) and needs to return to whichever one it
came from. `App.jsx` tracks this with one small piece of state,
`suggestedProfilesOrigin` (`"summary" | "dashboard"`), set immediately
before each transition into that stage.

## 6. Start Experience

A single, unconditional CTA — it does not gate on whether a profile or a
selection exists. This mirrors the existing demo flow, where
`TaskEnvironmentPage`/barrier detection/adaptation recommendation already
work correctly against an all-typical Ability Profile (they simply find
no barriers). Nothing about that pipeline changed; the Dashboard's button
is a UI entry point only (`setStage("task-environment")`), never a
computation.

`TaskEnvironmentPage`'s existing "Back to Profile Summary" button now
returns an authenticated ("account" `entryMode`) visitor to the Dashboard
instead of the raw Profile Summary screen; a demo persona's identical
button is completely unchanged (`entryMode === "demo"` still goes to
`"summary"`). This is a one-line change to which stage the existing
`onBackToSummary` callback lands on in `App.jsx` — `TaskEnvironmentPage.jsx`
itself was not modified, and its button label ("Back to Profile Summary")
was deliberately left as-is rather than expanding this phase's diff to
thread a second label variant through it; the destination it now reaches
still shows the same Ability Profile summary, just alongside Selected
Profiles and Start Experience.

## 7. Security / ownership

No new endpoint, so no new ownership surface. `DashboardPage` only ever
calls `getProfileSuggestions(userId)`/`getProfileSelections(userId)` with
`userId = user.id` from the authenticated `useAuth()` hook — never a
route param or any other client-suppliable value — so the existing
`assert_owner()` checks on those two endpoints (Phase 3) are exercised
exactly as before; there is nothing for a second user's id to reach.

**Authentication guard:** nothing in the UI can normally set `stage` to
`"dashboard"` while logged out — every path into it
(`handleGoToDashboard`, `handleSuggestedProfilesComplete`) only runs from
an already-authenticated branch. As defense in depth, `App.jsx` has a
dedicated effect: if `stage === "dashboard"` and `auth.isAuthenticated`
becomes false while `entered` is still true (a token silently expiring
mid-visit), it returns to the landing page. The Dashboard's own "Log out"
button does this synchronously and explicitly instead of relying on that
effect's next render (`handleLogout` now sets `entered` to `false`
directly), so there is no frame where a stale, personalized page is
rendered against a `null` user after an intentional logout click.

Verified live (Playwright): a brand-new account's first Dashboard visit
shows the correct empty states; completing onboarding returns to a
populated Dashboard; "Manage Profiles" → "Back" returns to the Dashboard;
"Edit Ability Profile" reaches the manual editor directly; "Start
Experience" reaches Task & Environment and its own "Back" returns to the
Dashboard for an account user; logging out returns to the Landing page
with no stale data rendered; a page reload never shows a leftover
Dashboard; re-logging in as an already-onboarded user lands on the
populated Dashboard directly, with no forced re-onboarding. Zero
console/page errors across every run. The pre-existing anonymous demo
persona flow (`SelectUserPage` → Consent → the manual editor, never the
questionnaire) was re-verified unchanged.

## 8. Loading / error / empty states

- **Ability Profile card:** no loading state needed — `profile` is a prop
  already resolved before this page renders. Empty state per §4; error
  state inherited from `useProfileFlow` elsewhere (unchanged).
- **Selected Profiles card:** `loading` → "Loading your selected
  profiles…"; `error` → a distinct message for an expired/invalid session
  (`401`/`403`, with a "Log in again" button that calls the same
  `onLogout`) versus any other failure (network/500, with a "Retry"
  button that re-runs the fetch); `ready` with zero selections → the
  explicit empty-state message described in §5.
- **Start Experience card:** static; no data dependency, so no loading/
  error state of its own.

## 9. What was deferred

Out of scope for this phase, per its own restrictions:

- No authenticated-user integration into the orchestrator, barrier
  detection, or adaptation engine — "Start Experience" is an entry point
  into the existing standalone Task & Environment screens only, exactly
  as `SuggestedProfilesPage`'s "Continue" already was before this phase.
- No new barriers, adaptations, AI personalization, or scoring changes.
- No session history/analytics redesign — the existing `AnalyticsPage` is
  untouched and unreferenced from the Dashboard.
- No React Router migration — `"dashboard"` is one more value in
  `App.jsx`'s existing `stage` state machine, nothing more.
- No new database model, migration, serializer, or view — see §2.
- `TaskEnvironmentPage.jsx`'s `profileLabel` (shown as "Selected user: —"/
  "Selected Ability Profile: —") is blank for every real account, because
  `AbilityProfile.label` is only ever populated by `seed_demo.py`'s demo
  personas, never by the questionnaire or manual editor. This is a
  pre-existing gap that predates Phase 4 (any account user reaching this
  screen via Phase 3's flow already saw it) and is left as a known
  limitation rather than expanding this phase's scope to backfill a label
  for real accounts.
- Applying a selected profile's own dimensions onto the real
  `AbilityProfile` is still not implemented (`docs/PROFILE_SUGGESTIONS.md`
  §8/§11) — the Dashboard only ever *displays* selections, exactly as
  `SuggestedProfilesPage` only ever recorded them.
