# Authenticated Experience (Phase 5)

> **Scope note:** covers register→login (Phase 1) → consent/questionnaire
> (Phase 2) → profile suggestions (Phase 3) → Dashboard (Phase 4) → the
> real, session-based AbilityOS reasoning pipeline (barrier detection →
> adaptation → safety validation → adaptive kiosk → outcome → feedback),
> which already existed and is now reachable end-to-end by a real
> registered user, not only by a demo persona.

## 1. Purpose

Make this statement true: a real registered user can use their own
AbilityProfile to run the exact same AbilityOS reasoning and adaptive
interaction pipeline that already worked for demo personas. Nothing about
*how* the engine reasons changed — only how a real account reaches it.

## 2. Authenticated user flow

```
Login
  ↓
Dashboard  (Phase 4 — Ability Profile summary, Selected Profiles, Start Experience)
  ↓  (first visit only, if consent isn't granted yet: "Grant Consent" → ConsentPage → Questionnaire)
  ↓
Start Experience
  ↓
Task & Environment  (TaskEnvironmentPage.jsx, unmodified — Analyze Task / Analyze Environment /
  ↓                   Detect Barriers / Recommend Adaptation, all against this account's own profile)
Open Adaptive Kiosk
  ↓
DemoPage.jsx + useAbilityOSDemo.js + KioskView.jsx  (all unmodified)
  ↓
POST /interactions/start/ → environment/analyze → barriers/detect → adaptations/recommend → apply
  ↓
Adaptive Kiosk interaction (real, not decorative — see KioskView.jsx's own docstring)
  ↓
complete/abandon → Outcome
  ↓
Feedback → session summary (outcome score, learning signal)
```

## 3. Demo user flow (unchanged)

```
Landing → Explore AbilityOS → Select Demo Persona → Consent →
Manual Ability Profile Editor → Profile Summary → Task & Environment →
Open Adaptive Kiosk → (the same DemoPage/useAbilityOSDemo/KioskView as above)
```

Re-verified live after this phase's changes (see §11): all 9 demo personas
still selectable, the manual editor (never the questionnaire) is still
what a demo persona reaches after consent, "Back to Profile Summary"
still returns to Profile Summary (not the Dashboard, which doesn't exist
for `entryMode === "demo"`), zero console errors.

## 4. Shared reasoning architecture

There is exactly one reasoning pipeline, and Phase 5 added no second one:

```
Demo User ─────────────┐
                        ↓
                  api.services.orchestrator.InteractionOrchestrator
                  (barriers.services.detection, adaptations.services.rules,
                   ai_engine.services.decision_engine — all unmodified)
                        ↑
                        │
Authenticated User ─────┘
```

`InteractionOrchestrator.start(user, task_id, environment_id, baseline_mode)`
(`backend/api/services/orchestrator.py`) takes a Django `User` instance —
it has never distinguished a demo persona from a real account, because
nothing about a `User` row's origin is visible to it. The same is true one
level up: `frontend/src/pages/DemoPage.jsx`, `useAbilityOSDemo.js`, and
`KioskView.jsx` all take a plain `userId`/`profile` prop and were **not
modified in this phase** — they already had no idea whether that id came
from `SelectUserPage` (a demo persona) or `App.jsx`'s `flow.selectUser(auth.user.id)`
(a real account, wired since Phase 2's `handleQuestionnaireComplete`).
Phase 5's job turned out to be almost entirely about the two screens
*before* that point — Dashboard's entry gating — not the engine itself.

## 5. AbilityProfile source

Always `abilities.models.AbilityProfile`, fetched via the existing
`abilities.services.profile_service.get_or_create_profile()` /
`AbilityProfileSerializer` — the same model and service every prior phase
used. No second profile object, no frontend-constructed dimensions dict
ever reaches the engine: `InteractionOrchestrator.start()` re-reads the
profile from the database by `user`, and `detect_barriers()`/
`recommend_adaptations()` do the same (`AbilityProfile.objects.get(user=session.user)`)
rather than trusting anything passed in from a prior request.

## 6. InteractionSession ownership

Unchanged, and already correct before this phase: every session-scoped
endpoint (`analyze environment`, `detect barriers`, `recommend
adaptations`, `apply`, `events`, `complete`, `abandon`, `feedback`,
`summary`) resolves the session by id and then calls
`users.services.ownership.assert_owner(request, session.user_id, ...)` --
a no-op for an anonymous (demo) request, and a hard 403 for an
authenticated request whose `request.user` isn't the session's owner (or
staff). `StartInteractionView` applies the same check to the `user_id` a
request supplies before using it. This is the exact mechanism Phase 5's
own brief asks for ("request.user must determine ownership") --
implemented in Phase 1/8, re-verified (not re-built) here with a new,
dedicated test suite using two genuinely separate *registered* accounts
rather than demo personas standing in for one (`RealUserOwnershipTests`,
`backend/api/test_authenticated_pipeline.py`).

## 7. Profile snapshot behaviour

Unchanged. `InteractionOrchestrator.start()` already does
`ability_profile_snapshot=copy.deepcopy(profile.dimensions)` at session
creation, for every session regardless of whose account it belongs to. A
real account editing their profile mid-session (via the Dashboard's "Edit
Ability Profile", reaching `AbilityProfileEditorPage`) does not retroactively
change an in-progress session's snapshot -- `InteractionOrchestrator.summary()`
always returns the session's own `ability_profile_snapshot`, never a live
re-read. Verified by `test_real_authenticated_user_runs_the_full_pipeline`'s
snapshot assertion.

## 8. Consent requirement

`users.services.consent_service.is_consented_for_adaptation(user)` is
still the sole authority, checked inside `InteractionOrchestrator.start()`
itself (raises `OrchestratorError`, mapped to HTTP 409 by
`api.exceptions.abilityos_exception_handler`) -- unchanged. What Phase 5
added is a **frontend** gate in front of that: Dashboard's "Start
Experience" card now reads `flow.consent?.granted` (already fetched by
`useProfileFlow.selectUser`, no new request) and shows "Grant Consent"
instead of the CTA when it's false, routing to the existing `ConsentPage`
via a new `handleGrantConsentFromDashboard` (`App.jsx`). This is a UX
improvement, not a new security boundary -- the backend already rejected
an unconsented session with 409 before this phase; a user could previously
only discover that by clicking "Start Experience" and hitting an inline
error deep in `TaskEnvironmentPage`.

`handleAgreeConsent` (`App.jsx`) was extended with one branch: granting
consent when the profile is *already* customized (the "Grant Consent"
path just described, for a returning account) returns straight to the
Dashboard instead of forcing a re-run of the questionnaire, which is
already what `entryMode === "account"` did for a *never*-onboarded user.
Both branches call the exact same `flow.agreeToConsent()` → the existing
`POST /api/users/{id}/consent/`.

## 9. Security / ownership

Audited every endpoint in the authenticated flow (profile retrieval,
consent, session start/analyze/detect/recommend/apply/events/complete/
abandon/feedback/summary, and the standalone barrier-detection/adaptation-
recommendation demo endpoints `TaskEnvironmentPage.jsx` calls). All of
them already called `assert_owner()` -- see §6. **No backend production
code was changed in this phase.** The two ownership gaps Phase 0 found
(`AbilityProfileView.get()`, `ConsentView.get()`) were already fixed in
Phase 1 and were re-verified, not re-fixed, here (`assert_owner()` calls
still present in both, confirmed by reading `abilities/views.py` and
`users/views.py` and by `RealUserOwnershipTests.test_user_a_cannot_read_user_bs_ability_profile`).

New test coverage specifically for two genuinely separate *registered*
accounts (not demo personas force-authenticated, which
`Phase8OwnershipAndHardeningTests` already covered): User A cannot start a
session using User B's id, cannot read User B's Ability Profile, cannot
read/apply-to/submit-feedback-for User B's session -- all 403.

## 10. Barrier detection integration

Unchanged (`barriers/services/detection.py`, `barriers/services/detector.py`
untouched). Proved equivalent, not merely "not broken", by
`DemoVsAuthenticatedEquivalenceTests`: the seeded `demo_low_vision_dexterity`
persona and a fresh registered account given the identical two trigger
dimensions (`vision: large-text-needed`, `dexterity: reduced-precision`)
produce the same barrier-type set and the same approved-adaptation names
through the real session pipeline (Phase 5 section 31's explicit
acceptance criterion). Verified live too -- the authenticated e2e run's
Detected Barriers panel showed `audio_only_alert` + `low_contrast` for
that run's own vision/hearing answers, exactly the barrier types those
dimensions trigger for any profile, demo or real.

## 11. Adaptation integration

Unchanged (`adaptations/services/rules.py`, `adaptations/services/recommender.py`,
`ai_engine/services/decision_engine.py` untouched). The live e2e run's
Developer Panel shows the real deterministic-fallback rationale ("no AI
provider configured... Accessibility Benefit + Task Relevance + User
Preference + Confidence − Interaction Cost − Risk") for a real account,
identical in form to what a demo persona's run shows.

## 12. Safety validation

Unchanged (`adaptations.services.rules.validate_adaptation`, called from
`InteractionOrchestrator.recommend_adaptations()` for every session
regardless of owner). No authenticated-only bypass exists or was added --
grep of the orchestrator confirms `validate_adaptation` is called
unconditionally, once, in the one shared code path.

## 13. Feedback

Unchanged (`feedback.models.Feedback`, `InteractionOrchestrator.record_feedback()`).
`InteractionFeedbackView` already enforced `assert_owner()` against
`session.user_id`, so a real account can only ever submit feedback for
its own session -- proved directly (not just inferred) by
`RealUserOwnershipTests.test_user_a_cannot_submit_feedback_for_user_bs_session`.
Verified live: the e2e run's feedback form (ease rating, adaptation
helpfulness, assistance) submitted successfully and the resulting outcome
score / learning signal appeared on the real account's session summary.

## 14. Known limitations

- `AbilityProfile.label` is only ever populated by `seed_demo.py`'s nine
  demo personas -- no code path sets it for a real account (already noted
  in `docs/DASHBOARD.md`). This phase added a fallback everywhere a blank
  label would otherwise read oddly to an authenticated user
  (`TaskEnvironmentPage`'s `profileLabel` prop now receives the account's
  own display name/username from `App.jsx`; `DemoPage.jsx`'s heading falls
  back to "your Ability Profile"). One place was deliberately **not**
  touched: `DeveloperPanel`'s "User: —" line, which is a
  developer/explanation surface (not the primary user-facing UI) already
  shown identically during the demo flow -- fixing it would mean adding a
  new prop through a third component for a purely cosmetic, non-blocking
  gap, which this phase's "keep fixes focused" boundary argues against.
- Anonymous (unauthenticated) requests remain unrestricted by ownership on
  every `AllowAny` endpoint, **including for a real account's numeric id**
  -- this is a pre-existing, explicitly documented design choice
  (`users/services/ownership.py`'s own docstring: "the anonymous
  hackathon-demo path... is left open by design") that predates this
  phase and was deliberately not narrowed here. `is_consented_for_adaptation`
  still gates *use* of a profile for adaptation for every caller
  regardless of authentication, but an anonymous caller who knows a real
  user's numeric id can still read that user's Ability Profile or start a
  session using it, exactly as they could for any demo persona's id
  before this phase. Closing this would mean requiring authentication on
  endpoints the anonymous demo also depends on -- a materially larger,
  separate security change than "connect authenticated users to the
  existing engine," left out per section 12's explicit "do not turn Phase
  5 into a complete security rewrite" boundary. See
  `RealUserOwnershipTests.test_unauthenticated_request_cannot_use_a_real_users_id_to_start_a_session_they_should_not_bypass_consent`,
  which documents (rather than hides) this behaviour.
- Header's "Reset Demo" control (shown on the Task & Environment / Kiosk /
  Analytics screens for both entry modes) still always returns to
  `SelectUserPage` regardless of `entryMode` -- a pre-existing, Phase-4-and-earlier
  quirk for an authenticated user who clicks it mid-experience. Not
  changed here: fixing it would mean threading `entryMode` into `Header.jsx`,
  a broader touch than this phase's scope, and it's reachable but not part
  of any flow this phase's acceptance criteria name.
- No dimension-completeness gate exists (or was added) on "Start
  Experience" -- only consent is enforced, because consent is the only
  rule the existing service layer (`consent_service.is_consented_for_adaptation`)
  actually authors as a precondition for using a profile. A profile still
  at its all-default/typical dimensions is treated as valid (the engine
  simply finds no barriers), the same way a demo persona with a typical
  profile would be. Inventing a second, undocumented "completeness" rule
  was deliberately avoided (section 9: "do not duplicate validation
  rules... the existing profile validation/service layer must remain
  authoritative").

## 15. Phase 6/7 boundaries

Not implemented, per this phase's explicit restrictions: session history
UI, analytics dashboard changes, AI profile learning, any new barrier/
adaptation/task/environment/kiosk implementation, a second authentication
system, React Router, or a frontend redesign. `AnalyticsPage`/`HistoryPage`
were not touched; `analytics.services` was not touched. Real sessions
created by authenticated users flow into the exact same `InteractionSession`/
`Feedback` rows the existing analytics aggregation already reads (`is_seed=False`,
same as any live demo session) -- no new leakage path, because there is no
new code path.
