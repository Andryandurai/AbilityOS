# Phase 6 — Adaptive Kiosk Experience

## Objective

Phase 5 only ever *decides*. Nothing in this codebase changed a single
pixel because of that decision until this phase. Phase 6 closes that loop:
it takes the adaptation Phase 5 already approved and safety-validated and
actually renders it — real layout changes, real behaviour changes, in the
same kiosk simulation used everywhere else in the demo.

> **Phase 5 decides. Phase 6 applies.** Nothing in this phase invents an
> adaptation, guesses one from the Ability Profile, or renders anything the
> backend didn't already approve.

## Core principle: the frontend never decides

There is no code anywhere in the frontend of the form
`if (dexterity === "reduced-precision") { ... }`. `KioskView` has exactly
one adaptation-relevant input, `appliedEffects` — a plain object it
receives as a prop, produced entirely server-side by
`InteractionOrchestrator.apply()` (pre-existing, unmodified by this
phase). If that object is empty, the kiosk renders standard. If it has
keys, the kiosk reads *only* the specific keys it recognizes and ignores
everything else — it never inspects the Ability Profile to decide whether
something needs to look different.

## Architecture

```
Phase 5: AdaptationDecisionPanel ("Open Adaptive Kiosk")
      │  (no data carried across — just a navigation trigger)
      ▼
DemoPage (pre-existing, unmodified pipeline)
      │
      ├─ POST /api/interactions/start/          )
      ├─ POST /api/environment/analyze/          )  same backend
      ├─ POST /api/barriers/detect/               )  re-derives the
      ├─ POST /api/adaptations/recommend/        )  decision from
      ├─ POST /api/interactions/<id>/apply/       )  scratch
      ▼
{ applied_adaptations: [...], ui_effects: {...}, baseline_mode }
      ▼
KioskView(appliedEffects, barriers, environment, interactive, ...)
      │  reads only known keys — button_scale, spacing_scale, text_scale,
      │  contrast, flow, choice_limit, voice_prompts, tts, banner_alert,
      │  haptics, confirm_step — via CSS custom properties + branches
      ▼
Real, interactive ticket-purchase kiosk with the adaptation actually live
```

### Why "Open Adaptive Kiosk" re-runs the pipeline instead of passing data through

The standalone Task & Environment screen (Phase 3/4/5) and the real kiosk
(`DemoPage`/`KioskView`, built earlier and never removed) are two
independent, parallel pipelines that both call the same deterministic
scoring/validation code and therefore always agree. Rather than take the
standalone screen's `AdaptationDecisionPanel` result and hand it directly
to `KioskView` as a prop, "Open Adaptive Kiosk" simply navigates to
`DemoPage`, which re-runs the full session-based pipeline
(start → analyze → detect → recommend → apply) against the backend from
nothing. This means there is no code path anywhere where a client-side
value reaches the kiosk without passing through backend safety validation
again — the alternative (threading the standalone result through as a
prop) would have created exactly the kind of "frontend decides" shortcut
this phase's core principle forbids.

## The "adaptation renderer"

The phase brief describes an adaptation registry mapping `adaptation_id`
→ render behaviour. This codebase already had an equivalent — arguably
better — mechanism from an earlier pass, and this phase deliberately kept
it rather than building a second one:

- Each `Adaptation` row carries `ui_effects`, a small JSON object of
  **presentation directives** (e.g. `{"button_scale": 1.8, "spacing_scale": 1.2}`),
  not an adaptation id.
- `InteractionOrchestrator.apply()` merges every applied adaptation's
  `ui_effects` into one dict and returns it.
- `KioskView` interprets that dict's *keys*, not adaptation ids.

This is a strictly smaller trust surface than an id-keyed registry: adding
a 13th catalogue adaptation that reuses `button_scale` requires zero
frontend changes, and the frontend never needs to know adaptation names at
all — only the fixed, allowlisted effect-key vocabulary
(`adaptations/services/config.py::ALLOWED_UI_EFFECT_KEYS`, the same list
Phase 5's safety validator already enforces server-side). `KioskView`'s
effect-key handling **is** the renderer; it was not rebuilt for this
phase, only exercised for the first time.

## Kiosk flow

1. Select User → Consent → Ability Profile → Profile Summary (unchanged,
   Phase 2).
2. Task & Environment: Analyze Task → Analyze Environment → Detect
   Barriers → Recommend Adaptation (unchanged, Phase 3/4/5).
3. **New this phase:** "Open Adaptive Kiosk" button on
   `AdaptationDecisionPanel`, shown only once the backend has approved a
   selection. Navigates into the real kiosk.
4. Real kiosk: "Start Ticket Purchase" re-runs start/analyze/detect/
   recommend against the session-based endpoints; "Apply Approved
   Adaptation(s)" (or the confirmation dialog, for a `requires_confirmation`
   adaptation) calls `/apply/` and the interface changes live.
5. The **Adaptation Indicator** (`✓ Interface personalized for easier
   interaction`) appears the moment `appliedEffects` is non-empty —
   respectful, functional language, no diagnostic or medical terms
   anywhere.
6. **View Original / View Adaptive** toggle (demonstration-only):
   re-renders the same `KioskView` with `appliedEffects={}` for
   "Original". It does not call a different endpoint, skip validation, or
   fall back to a second code path — it is the identical component with an
   empty effects object, so there is no way for the comparison to diverge
   from what the backend actually approved.
7. Completing the task calls the existing feedback endpoint; the
   Before/After panel (already built) picks it up.

## Supported adaptations (12, unchanged from Phase 5's catalogue)

| `ui_effects` key | What `KioskView` does with it |
|---|---|
| `button_scale` | Scales tap targets via `--button-scale`; also removes the reduced-dexterity miss-chance simulation once a control is comfortably sized |
| `spacing_scale` | Scales gaps between controls via `--spacing-scale` |
| `contrast` (`"high"`) | Switches the kiosk to the high-contrast palette; clears the "unresolved low-contrast" visual state |
| `text_scale` | Scales all kiosk text via `--text-scale` |
| `flow` (`"guided"`/`"simplified"`) | Switches from "everything on one screen" to a one-step-at-a-time flow with a visible step counter |
| `choice_limit` | Paired with `flow`; bounds how many options are shown per step |
| `voice_prompts` / `tts` | Speaks the current step / result via the Web Speech API (`speechSynthesis`), wrapped in try/catch |
| `banner_alert` | Mirrors the kiosk's audio-only purchase alert as an on-screen banner |
| `haptics` | Fires `navigator.vibrate(...)` alongside a successful tap or the purchase result |
| `confirm_step` | Inserts an explicit "Yes, buy / Cancel" step before an irreversible purchase |
| `voice_input` | Present in `ui_effects` for `alternative_voice_input` (a `requires_confirmation`, high-risk adaptation); no full speech-recognition input exists in this hackathon prototype, so `KioskView` does not attempt to fabricate one — the adaptation still applies safely (indicator shown, no crash), the interaction itself is unchanged, which is the documented safe-degradation behaviour, not a bug |
| `progress_indicator` | Carried in the catalogue's `step_by_step_flow` entry; its visible effect (`Step X of Y`) is already produced by `flow: "guided"` above, so no separate handling is needed |

Any key outside this list is ignored by `KioskView` by construction (it
only ever reads the specific keys above) — this is what makes an unknown
or future adaptation "fail safe" without any explicit unknown-key check in
the rendering code itself. `DeveloperPanel` additionally surfaces a
visible (non-blocking) note if an applied adaptation's `ui_effects`
contains a key outside this vocabulary, purely so a developer can see it —
see `api/tests.py::Phase6KioskRenderingContractTests` for the backend side
of this contract.

## Original vs. Adaptive comparison

Demonstration-only, as required. "View Original" does not re-run barrier
detection, does not call a different backend path, and does not disable
consent or safety validation — it is the same `KioskView` given an empty
`appliedEffects` object, exactly like the pre-adaptation state that always
existed. Switching back to "View Adaptive" restores `state.appliedEffects`
from the same `apply()` response already returned once by the backend; it
never re-derives or invents a new one.

## Developer / System view

`DeveloperPanel.jsx` (built in an earlier pass) already showed the full
PERSON → PROFILE → TASK → ENVIRONMENT → BARRIER → DECISION → VALIDATION →
RESULT chain with real API responses. This phase adds:

- A `User:` line so the active demo profile is unambiguous at a glance.
- A consolidated `Applied: ✓ <names>` line summarizing what's actually
  live on the kiosk right now.
- A fix this addition exposed: the per-decision "applied to the
  interface" text and the new consolidated line were both about to read
  `AdaptationResult.applied`, which is fetched once at recommend-time and
  never refreshed after the later `/apply/` call — so it always read
  `false` even after a real apply. Both now derive "applied" from the
  `apply()` response's own `applied_adaptations` list (the actual source
  of truth), matched back to `results` by adaptation name.
- A non-blocking note if an applied adaptation carries an unrecognized
  `ui_effects` key (see the table above).

## No backend changes were required

Every endpoint Phase 6 needed — `/api/interactions/start/`,
`/api/environment/analyze/`, `/api/barriers/detect/`,
`/api/adaptations/recommend/`, `/api/interactions/<id>/apply/` — already
existed, unmodified, from earlier phases. `docs/API.md` has no new
contract to document for this phase. The only backend work was three new
tests (`api/tests.py::Phase6KioskRenderingContractTests`) pinning down
guarantees the kiosk UI depends on but that weren't previously asserted
directly.

## Safety behaviour

- Unknown/invalid adaptation → the standard kiosk renders (`appliedEffects`
  stays `{}` until a real, approved decision exists) — never a guess, never
  a crash.
- The Original/Adaptive toggle cannot desynchronize from what the backend
  approved, by construction (see above).
- Voice (`speechSynthesis`) and haptic (`navigator.vibrate`) calls are all
  wrapped in try/catch and are one-shot per event — nothing in this
  codebase listens continuously or records audio.
- `AdaptationDecisionPanel` shows a plain "Personalized adaptation is
  unavailable for this combination — the standard kiosk experience would
  be used" message (and no "Open Adaptive Kiosk" button) when nothing was
  approved, rather than implying a decision that doesn't exist.

## Accessibility

All new UI (the adaptation indicator, the View Original/Adaptive toggle,
the "Open Adaptive Kiosk" button) uses semantic buttons/roles
(`role="status"`, `aria-pressed`, `role="group"` with `aria-label`),
respects the existing skip-link and focus order, and inherits the kiosk's
existing `--text-scale`/`--button-scale`/`--spacing-scale` custom
properties rather than introducing a second styling system.

## Demo instructions

1. `python manage.py runserver 4343` (backend), `npm run dev` (frontend,
   port 3434 per `.env.local`).
2. Select a demo profile → agree to consent (pre-granted, still a real
   step) → Profile Summary → Continue to Task & Environment.
3. Analyze Task → Analyze Environment → Detect Barriers → Recommend
   Adaptation → **Open Adaptive Kiosk**.
4. Start Ticket Purchase → Apply Approved Adaptation(s) (confirm if
   prompted) → observe the adaptation indicator and the changed layout →
   toggle View Original/View Adaptive to compare → complete the purchase.
5. Repeat with a second demo profile to see a different barrier produce a
   different, independently-approved adaptation.

## Test matrix (verified live via Playwright, headless Chromium)

| Profile | Barrier(s) detected | Approved adaptation(s) | Expected kiosk UI |
|---|---|---|---|
| Low Vision + Reduced Dexterity | `small_tap_targets`, `low_contrast` | Increase target size, Increase contrast | Larger buttons (`button_scale` 1.8, `spacing_scale` 1.2), high-contrast palette + larger text (`text_scale` 1.3), adaptation indicator shown |
| Hearing Difficulty | `audio_only_alert` | Caption / mirror audio alerts | The purchase-result audio alert is mirrored as an on-screen banner plus a vibration; adaptation indicator shown |
| Cognitive Load | `too_many_choices` | Step-by-step guided flow | One-question-at-a-time flow with a visible "Step X of Y" indicator instead of all fields on one screen; adaptation indicator shown |
| Any profile, "View Original" selected | (same as above) | (same as above, unapplied) | Adaptation indicator hidden, small/standard controls, no guided flow — same barriers still exist, just unaddressed |
| Any profile, no barriers for this task/environment | none | none | Standard kiosk, no indicator, "Open Adaptive Kiosk" / apply flow simply has nothing to apply |

## Testing performed

- `npx oxlint src` — clean (only pre-existing warnings in files this phase
  didn't touch: `DemoPage.jsx` effect-based resets, `KioskView.jsx`'s
  pre-existing `performance.now()`/`Math.random()` usage).
- `npm run build` — succeeds.
- `python manage.py test` — **187/187 pass** (184 pre-existing + 3 new
  `Phase6KioskRenderingContractTests`: applying an adaptation does not
  mutate the `Task`/`TaskStep` rows Phase 3 described; the apply response's
  `applied_adaptations` list matches the `AdaptationResult.applied=True`
  rows in the database; an unrecognized `ui_effects` key merges into the
  response without a server error).
- Live Playwright walkthrough of the full flow (Select User → Consent →
  Profile → Summary → Task & Environment → Analyze/Detect/Recommend →
  Open Adaptive Kiosk → Start → Apply → toggle Original/Adaptive →
  complete) for two demo profiles (Low Vision + Reduced Dexterity, Hearing
  Difficulty): adaptation indicator appears/disappears correctly with the
  toggle, Developer Panel's `User:` and `Applied:` lines render correctly,
  no browser console errors.

## Known limitations

- `alternative_voice_input`'s `voice_input` effect key has no corresponding
  speech-recognition implementation in this hackathon prototype (documented
  above as intentional safe degradation, not a bug).
- The Original/Adaptive toggle is demonstration-only UI state (`viewMode`
  in `DemoPage`), not a persisted preference — it resets on navigating away,
  matching every other in-session-only piece of state in this pipeline.
- No new automated frontend tests were added (this project has no
  Jest/Vitest harness configured); verification is `oxlint` + `vite build`
  + a live Playwright walkthrough, consistent with how every prior phase's
  frontend work was verified.

## Phase 7 boundary

Nothing in this phase adds feedback persistence, analytics, or a learning
loop beyond what already existed from an earlier pass (the
`InteractionFeedbackView`/`AnalyticsPage`/before-after metrics panel were
already built and are left exactly as they were — not extended, not
removed). This phase only makes the kiosk actually *apply* what Phase 5
already approved.
