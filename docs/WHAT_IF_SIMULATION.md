# Phase 7 — Advanced Adaptive Intelligence, What-If Simulation & Decision Support

> **Naming note:** this session's own "Phase 7" (Auth → Onboarding →
> Suggestions → Dashboard → Authenticated Experience → History →
> **What-If Simulation**) is a separate numbering from this repository's
> pre-existing `docs/PHASE_3.md`–`docs/PHASE_8.md` (the original
> reasoning-engine build: Task/Environment Understanding, Barrier
> Detection, the Adaptation + AI Decision Engine, the Adaptive Kiosk, and
> Feedback/Analytics/Learning). Both numbering schemes happen to reach
> "Phase 7," so this document is named for its actual content —
> What-If Simulation — rather than `docs/PHASE_7.md`, which remains the
> pre-existing "Feedback, Interaction Analytics & Adaptive Learning" doc
> and was **not** touched by this work. (An earlier draft of this file
> briefly overwrote that pre-existing `docs/PHASE_7.md` by mistake; it was
> restored from git and this document was saved under its own name
> instead — noted here for transparency, not because it affects anything
> going forward.)
>
> **Scope note:** builds on Phase 5/6's authenticated pipeline and history.
> Nothing about how barriers or adaptations are actually detected/decided
> changed in this phase — What-If calls the exact same functions a real
> (non-simulated) request already used.

## 1. Phase objective

Extend AbilityOS from "detect barrier → apply adaptation" toward "detect
barrier → explain why → evaluate candidates → safely apply one → allow
controlled what-if analysis" — without a second reasoning engine, a second
AbilityProfile schema, or any change to how a *real* decision is made.

**AbilityOS does not diagnose disabilities or medical conditions.** What-If
answers "what makes this task difficult in this environment, functionally,"
never "what condition does this person have."

## 2. What-If architecture

```
                    ┌─────────────────────────┐
Authenticated User  │  request.user's REAL     │
        │           │  AbilityProfile.dimensions│  (never mutated)
        ▼           └────────────┬─────────────┘
POST /api/what-if/simulate/      │
{task_id, overrides:{dexterity:"typical"}}
        │                        │
        ▼                        ▼
   validate_overrides()   build_simulated_dimensions()
   (abilities.constants   (deepcopy + override one
    DIMENSION_KEYS/               level only)
    ALLOWED_LEVELS)
        │                        │
        ▼                        ▼
AdaptationRecommender.recommend(real_dims, task, env, modality)
AdaptationRecommender.recommend(simulated_dims, task, env, modality)
   (the EXISTING standalone pipeline — Phase 3/4/5, unmodified:
    BarrierDetectionService.detect() → scoring → optional AI ranking
    → AdaptationSafetyValidator.validate())
        │                        │
        └───────────┬────────────┘
                     ▼
              factual diff (_diff)
                     ▼
      {current, simulated, changes} — returned, nothing persisted
```

`backend/api/services/what_if.py` is the entire new backend logic: two
small pure functions (`validate_overrides`, `build_simulated_dimensions`)
plus `simulate()`, which calls `AdaptationRecommender.recommend()` — the
same function `RecommendAdaptationsView._recommend_standalone` already
uses for a real profile — exactly twice. No new barrier engine, no new
scoring, no new safety validator, no new AI plumbing.

## 3. Simulation lifecycle

1. Frontend (`WhatIfPage.jsx`) picks one dimension + one simulated value
   from the existing `ABILITY_QUESTIONS` constant (Phase 2) — the same
   controlled vocabulary the questionnaire and manual editor already use.
2. `POST /api/what-if/simulate/` with `{task_id, overrides}`.
3. Backend authenticates, loads `request.user`'s real `AbilityProfile`,
   validates the override against `abilities.constants`, builds a
   temporary in-memory dimensions dict (never saved), runs the existing
   pipeline twice, returns the comparison.
4. Nothing is written anywhere. The response is discarded by the frontend
   the moment the user navigates away — there is no simulation history to
   retrieve later (see §11).

## 4. Existing engine reuse

| Concern | Reused from | Changed? |
|---|---|---|
| Barrier detection | `barriers.services.detector.BarrierDetectionService.detect()` (called internally by `AdaptationRecommender.recommend()`) | No |
| Candidate generation + scoring | `adaptations.services.scoring.rank_candidates_for_barrier()` (Accessibility Benefit + Task Relevance + User Preference + Confidence − Interaction Cost − Risk) | No |
| AI ranking | `adaptations.services.recommender.AdaptationRecommender._decide()` / `ai_engine.services.llm_client` | No |
| Safety validation | `adaptations.services.validator.AdaptationSafetyValidator.validate()` | No |
| Ability vocabulary | `abilities.constants.DIMENSION_KEYS` / `ALLOWED_LEVELS` | No |

**A genuine pre-existing fact surfaced by this phase's own inspection,
not a bug introduced here:** the codebase has two independently-built
barrier-rule sets — `barriers/services/detection.py` (the session-based
pipeline `InteractionOrchestrator` uses) and `barriers/services/rules.py`
(the standalone pipeline `AdaptationRecommender`/`BarrierDetectionService`
use, which is what What-If also uses). They are *not* byte-identical:
for example `rules.py`'s low-contrast rule only triggers for
`vision: low-contrast-sensitive` (not also `large-text-needed`, unlike
`detection.py`), and its barrier-type string is `"low_contrast_text"`
rather than `"low_contrast"`. This predates this session's Phase 7 (it
already existed across the session-based Kiosk path vs. the standalone
Task & Environment demo path since the original build's Phase 4/5) and
was deliberately **not** touched here — consolidating two
independently-tested rule engines is a "broad refactor" explicitly out of
this phase's scope, not a "smallest safe fix." What-If is internally
consistent with itself and with the *other* standalone endpoints
(`GET /api/barriers/detect/` / `GET /api/adaptations/recommend/` in
standalone mode) — proven directly by `WhatIfConsistencyWithExistingEngineTests`
— which is the guarantee that actually matters for this feature.

## 5. Adaptation scoring

Unchanged formula, unchanged weights (`adaptations/services/config.py`).
`WhatIfPage.jsx` exposes it transparently by reusing the existing
`AdaptationDecisionPanel` component (built earlier in this session, for
Task & Environment) for both the current and simulated results: every
candidate's score, the selected adaptation's rationale, and whether AI or
the deterministic fallback chose it are all shown exactly as they already
were on Task & Environment's own "Recommend Adaptation" step. Nothing
here turns the score into a user-facing "rating" of the person — it is
presented per-adaptation, the same as before.

## 6. AI role

`AdaptationRecommender.recommend()` already implements "the LLM proposes,
the rule engine disposes": if `llm_client.is_configured()`, the AI ranks
only the deterministically-generated candidate pool and its choice is
re-validated against that pool before being trusted (an unknown
adaptation id, malformed JSON, or a Pydantic validation failure all fall
back to the deterministic top-scored candidate, logged, never crashing
the request). What-If calls this function unchanged, so it inherits every
one of these guarantees without re-implementing them. `WhatIfAIIntegrationTests`
proves the *delegation* itself works (a mocked valid AI response is
reflected as `source: "ai"`; a mocked response naming an adaptation
outside the pool, or invalid JSON, both fall back safely) — the AI-safety
logic itself is already unit-tested directly in
`adaptations/test_recommender.py` and was not duplicated here.

## 7. Safety validation

`AdaptationSafetyValidator.validate()` runs for both the current and
simulated results, unconditionally — there is no `if simulation: skip`
branch anywhere in `what_if.py` or `AdaptationRecommender.recommend()`.
A rejected candidate is never returned as `selected_adaptation`; the
existing next-safest-candidate fallback (already built into
`AdaptationRecommender.recommend()`) applies identically to a simulated
profile.

## 8. Feedback & learning signals

The existing `Feedback`/`analytics.services.generate_learning_signal()`
infrastructure was not duplicated or extended by What-If itself (a
simulation has no session, so there is nothing to attach feedback to —
see §11). What this phase *does* add is surfacing the already-computed
learning signal that was accessible but not yet rendered: `HistoryPage.jsx`'s
session detail view now also shows the existing `outcome_score` and
`learning_signal` fields from `GET /api/interactions/{id}/summary/`
(unchanged endpoint, unchanged computation — `analytics.services.calculate_outcome_score`/
`generate_learning_signal`), phrased in the descriptive
"Applied → completed → positive" style the spec asks for, for real past
sessions.

## 9. API design

One new endpoint:

| Endpoint | Method | Auth | Side effects |
|---|---|---|---|
| `/api/what-if/simulate/` | POST | `IsAuthenticated` + consent | **None** |

Request: `{"task_id": "purchase_ticket", "environment_id"?: "kiosk_standard", "overrides": {"dexterity": "typical"}}`.
`environment_id` defaults to `kiosk_standard` (the same
`DEFAULT_ENVIRONMENT_ID` `InteractionOrchestrator.start()` already uses)
if omitted. `overrides` must be a non-empty dict of `{dimension: value}`
pairs validated against `abilities.constants`.

Consent is required, matching the existing standalone barrier/adaptation
demo endpoints (`DetectBarriersView._detect_standalone`,
`RecommendAdaptationsView._recommend_standalone`) this reuses the same
engine as — What-If is the same shape of request (profile + task +
environment → barriers + adaptations, no session), so it is held to the
same rule they already are, not a new or looser one.

## 10. Ownership / security

The real `AbilityProfile` is always `get_or_create_profile(request.user)`
— there is no `user_id` request field at all, so there is nothing for a
client to spoof. Verified directly: two different authenticated accounts
calling the same endpoint each only ever see their own profile's
dimensions in the response (`WhatIfOwnershipTests`), and an explicit
(bogus, unsupported) `user_id` in the request body is simply ignored.
Anonymous requests are rejected outright (401); an authenticated user
without consent is rejected (403) before any profile data is touched.

## 11. Side-effect guarantees

**Running a simulation never writes anything.** `what_if.py` never
imports `apply_manual_update`, never instantiates `InteractionSession`,
never touches `UserProfileSelection`, `Feedback`, `QuestionnaireResponse`,
or `ConsentRecord`. Verified directly, not just asserted:
`WhatIfSideEffectTests` confirms the real `AbilityProfile.dimensions`,
the `InteractionSession` count, the `UserProfileSelection` count, and
consent state are all byte-for-byte unchanged after running a simulation
(including three simulations in a row, to rule out any silent
accumulation). There is deliberately no "simulation history" — a
What-If result exists only in the HTTP response and the frontend's local
component state; it is never persisted, so it can never be confused with
a real historical session on the History page.

> What-If simulations are temporary evaluations and do not modify the
> user's real AbilityProfile or historical session data.

## 12. Frontend flow

```
Dashboard ("Explore What-If", gated on consent same as "Start Experience")
        ↓
WhatIfPage.jsx
        ↓
Current Profile (existing summarizeProfile() formatter — same language as
                  Dashboard/History)
        ↓
Select a dimension (ABILITY_QUESTIONS) → current value (read-only, from
        the real profile) → simulated value (same dimension's own allowed
        options)
        ↓
Run Simulation → POST /api/what-if/simulate/
        ↓
Current State / Simulated State — both the EXISTING AdaptationDecisionPanel
        component, reused unmodified, onOpenKiosk intentionally omitted
        (nothing about a simulation opens the real kiosk)
        ↓
What Changed? — factual bullet list (barriers added/removed, adaptation
        changed), no subjective language
        ↓
"Simulation only. No changes were made to your profile or history."
```

Reached from Dashboard's "Explore What-If" button or the Header's new
"What-If" shortcut (both opt-in, `entryMode === "account"` only — the
demo flow's Header is unaffected, verified live). `App.jsx` adds one new
`"what-if"` stage to the existing state machine — no React Router
introduced.

## 13. Testing

**Backend** (`backend/api/test_what_if.py`, 24 tests): authentication
(anonymous rejected), consent gate, override validation (unknown
dimension/value, missing task_id/overrides, unknown task/environment →
404), correct barrier/adaptation changes for a real override, ownership
(two real accounts, query-parameter/body spoofing has no effect),
side-effect freedom (profile/session/selection/consent all unchanged,
including after repeated runs), consistency with the existing standalone
`/api/adaptations/recommend/` endpoint, and AI integration (valid AI
response reflected, out-of-pool AI selection falls back, malformed AI
output falls back, AI-unavailable path).

**Frontend**: live Playwright run — registered a user, set
`dexterity: reduced-precision` via the real questionnaire, opened What-If
from the Dashboard, selected the same dimension, ran a simulation showing
the `small_tap_targets` barrier removed and the adaptation changing to
"none required," confirmed the real profile was unchanged back on the
Dashboard, and confirmed the Header's "What-If" shortcut works mid-experience
— zero console errors throughout. Existing demo flow re-verified
unaffected (Header nav text is unchanged for `entryMode === "demo"`).

## 14. Known limitations

- The two barrier-rule engines' pre-existing minor divergence (§4) means a
  What-If simulation reflects the *standalone* engine's rules, which are
  not always identical to the session-based Kiosk pipeline's rules for
  every dimension/level combination. Both are internally consistent and
  already covered by their own respective test suites; reconciling them
  is future work, not a defect introduced by this phase.
- What-If only overrides one dimension per run in the current UI (the
  backend `overrides` dict technically accepts several dimensions at
  once) — matching the spec's own single-dimension mockup and keeping the
  page from becoming a multi-select analytics tool.
- No simulation result is ever saved or shareable — by design (§11), but
  worth noting: refreshing the page loses the last simulation.

## 15. Demo instructions

1. Register an account (or log in) and complete onboarding with at least
   one non-default dimension (e.g. dexterity → "Precise tapping can be
   difficult").
2. From the Dashboard, click **Explore What-If**.
3. Select the same dimension you customized, choose a different simulated
   value, click **Run Simulation**.
4. Compare **Current State** vs **Simulated State** — the barrier and
   selected adaptation for each are shown via the same panel the real
   Task & Environment screen uses.
5. Read **What Changed?** for the factual diff, and note the
   **Simulation only** disclaimer at the bottom.
6. Return to the Dashboard and confirm the real Ability Profile is
   unchanged.
