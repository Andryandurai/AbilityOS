# Phase 7 — Feedback, Interaction Analytics & Adaptive Learning

## 1. Objective

Phase 6 made an approved adaptation actually change the kiosk. Phase 7 answers the
next question:

> "Did that adaptation actually make the task easier, safer, faster, or more
> independent?"

The full loop is now: Person → Ability Profile → Task → Environment → Barrier →
Adaptation → Adaptive Interaction → **Outcome → Feedback → Analytics → Learning
Signal**. Phase 7 does not replace Phase 5's decision engine — it observes what
happened after a decision was applied and turns that into structured evidence a
future phase could use to improve recommendations. It never diagnoses a user and
never silently changes what the system decides.

## 2. What already existed vs. what this phase added

Before this phase, `feedback.InteractionSession` and `feedback.Feedback`, the
before/after and dashboard analytics endpoints, and an automatic profile-confidence
nudge already existed from an earlier pass — every subsequent phase's docs
(README, ARCHITECTURE.md, PHASE_5.md, PHASE_6.md) pointed at this as "Phase 7's
territory, already built, untouched." This phase extends those exact models and
endpoints rather than duplicating them, with one deliberate exception (section 4).

## 3. One deliberate correction: the retired auto-confidence hook

`InteractionOrchestrator._update_profile_confidence()` used to nudge a profile
dimension's `confidence` value (±0.05/−0.03) automatically after every feedback
submission. Tracing it through, that stored `confidence` value is one of the terms
in Phase 5's adaptation scoring formula — so it was silently shifting future
recommendations based on a single session's outcome, which is exactly what this
phase's own spec says not to do ("VERY IMPORTANT: do NOT automatically modify
[an ability dimension] based on one session... must NOT diagnose or automatically
infer medical conditions"; "[a learning signal] must not silently modify future
decisions").

This phase retires that automatic call. `record_feedback()` no longer touches the
Ability Profile at all — not even `confidence`. The two tests that asserted the old
behavior (`feedback/tests.py::LearningLoopTests`) now assert the opposite: that a
clean completion or a poor outcome leaves the profile's stored confidence
unchanged. `AbilityProfile.update_dimension_confidence()` itself is left in place
(it's generic, harmless model infrastructure) — it is simply never called
automatically again. Its replacement is the on-demand, non-mutating Learning
Signal (section 9).

## 4. Session lifecycle

`InteractionSession` (reused, not duplicated) gained two new statuses and a small
explicit state machine:

```
started → analyzed → adapted → in_progress → completed
                                            ↘ abandoned
                                            ↘ failed
```

Terminal statuses (`completed`/`abandoned`/`failed`) never transition anywhere —
`InteractionSession.transition_to()` raises rather than allowing a duplicate
completion or `completed → abandoned`. `completed_at` (new field) is set exactly
once, by whichever transition reaches a terminal status first, and
`completion_time_ms` is a computed property (`completed_at − created_at`) — the
server-authoritative duration Phase 7 asks for, independent of anything the
frontend measured locally.

Two snapshot-related fields the spec describes (`barrier_snapshot`,
`approved_adaptation`) were **not** added as new columns: the existing `Barrier`
and `AdaptationResult` rows are already FK'd to the session, created once, and
never mutated afterward (except the `confirmed`/`applied` flags) — they already
function as the immutable historical record the spec is asking for. Duplicating
that data as a second JSON snapshot would violate this phase's own "do not
duplicate" instruction for no benefit. `ability_profile_snapshot` (pre-existing)
continues to cover the "the user's current profile may later differ from what was
active during this session" concern directly.

## 5. Interaction events

New model: `feedback.InteractionEvent` (session FK, `step`, `event_type`,
`control_id`, a small bounded `metadata` dict, `created_at`). `event_type` is a
closed, controlled vocabulary (`control_selected`, `control_reselected`,
`validation_error`, `back_navigation`, `confirmation_opened`,
`confirmation_completed`, `assistance_requested`, `task_completed`,
`task_abandoned`, `step_started`) — an unrecognized value is rejected (400), never
silently accepted. `metadata` is capped at 10 keys and 200 characters per value
(`InteractionOrchestrator._sanitize_metadata`) — structured, task-relevant facts
only, never raw input, keystrokes, or recordings.

`KioskView.jsx` fires these at real interaction moments: selecting a
destination/ticket type (`control_selected`, or `control_reselected` if changing
an existing choice), a missed tap on a too-small target (`validation_error`), the
new guided-flow "← Back" control (`back_navigation`), opening/confirming the
purchase confirmation step (`confirmation_opened`/`confirmation_completed`), and
"Ask staff for help" (`assistance_requested`). Events are queued locally
(`useAbilityOSDemo.queueEvent`) and flushed in one batched
`POST /api/interactions/{id}/events/` call rather than one request per tap
(section 29) — flushed automatically right before `/complete/` or `/abandon/`.

`errors_count`/`retries_count`/`backtracks_count`/`assistance_count` are **derived**
from these events (`analytics.services.session_interaction_counts()`) rather than
maintained as separate, potentially-drifting counters — `InteractionEvent` is the
single source of truth for granular interaction facts. `InteractionSession.
assistance_count` is the one exception: it's denormalized onto the session row
(incremented by `record_event()`) purely so the Developer Panel and analytics can
read it without an extra query per session; `InteractionEvent` remains the
authoritative record it's derived from.

## 6. Assistance

Rule 31's "Need help?" control already existed in the Phase 6 kiosk as "Ask staff
for help" — this phase fixed its behavior rather than adding a second button: it
used to immediately end the task (conflating "I need a hand" with "I'm giving up").
It now records an `assistance_requested` event, increments `assistance_count`,
disables itself (so one request isn't silently multiplied by repeat clicks), and
lets the person keep going — satisfying the manual test script's explicit
"click Need help? → continue task → complete task" sequence. The distinct
"Leave without finishing" control (new) is the only path to an incomplete/abandoned
outcome now that "Ask for help" no longer doubles as one.

Assistance is never inferred from behavior — it only ever comes from this explicit
control, or the equivalent self-reported "Did you need help from another person?"
question on the feedback form (section 7), matching section 11's requirement.

## 7. Feedback

`Feedback` (reused, extended additively — no new model, no breaking migration):
`ease_rating` (1–5, `Feedback.EASE_CHOICES`), `adaptation_helpfulness`
(`helped`/`somewhat_helped`/`did_not_help`), `optional_comment` (truncated to 500
characters server-side). `assistance_requested` (pre-existing) already means
exactly what the spec calls `assistance_required` ("did you need a person's
help?") — reused under its existing name rather than duplicated.
`InteractionOrchestrator.record_feedback()` validates `ease_rating` and
`adaptation_helpfulness` against their controlled vocabularies and rejects (400)
anything else — no arbitrary uncontrolled values reach the database.

`FeedbackForm.jsx` is the three-question screen (plus optional comment), shown
once the task has already been marked complete/abandoned server-side — never
folded into the same moment as the objective outcome, matching the spec's
lifecycle diagram (task finishes → feedback is asked for, as a separate step).
Duplicate submission doesn't create a second row (`Feedback.session` is a
`OneToOneField`, and `record_feedback` uses `update_or_create`) — a second
submission updates the same row rather than being silently ignored or erroring.

`OutcomeSummary.jsx` then shows the user a plain-language recap (task name,
"Personalized interaction" vs. standard, their ease rating, whether the
adaptation helped, whether they needed assistance) — no barrier IDs, no
confidence scores, no adaptation-engine internals anywhere in this component
(section 25). That technical detail is exclusively in the Developer Panel.

## 8. Outcome Score

`analytics.services.calculate_outcome_score()` — a single 0.0–1.0 number per
session, deterministic, no AI:

```
score = completion × 0.35
      + assistance_reduction × 0.20
      + error_reduction × 0.20
      + ease_improvement × 0.20
      − time_penalty × 0.05
```

Every weight, cap, and threshold lives in `backend/analytics/config.py`, named and
documented — never an inline magic number. The weighting directly encodes section
19's priority ordering: completion and independence-from-assistance dominate;
`time_penalty` only ever subtracts a small amount, and only when the task itself
defines a `time_limit_seconds` (the seeded `purchase_ticket` task doesn't, so it
never applies in the current demo). A missing `ease_rating` scores a neutral 0.5
for that component — never silently treated as a bad (or good) rating.

## 9. Learning Signal

`analytics.services.generate_learning_signal()` — structured evidence about one
session, not a statistical claim:

```json
{ "adaptation_id": "increase_target_size", "task_id": "purchase_ticket",
  "barrier_type": "small_tap_targets", "successful": true,
  "independence_improved": true, "confidence": 0.3 }
```

`successful` = the task was completed. `independence_improved` = completed, no
assistance requested (neither the in-kiosk button nor the feedback form's
self-report), and (if rated) an ease of 4 or 5. `confidence` is always a fixed,
low `0.3` for a single session (`SINGLE_SESSION_CONFIDENCE` in config.py) — this
is deliberately never inflated to look like statistical certainty from one data
point. Returns `null` when there's no feedback yet or no adaptation was applied
this session (a baseline-mode or no-barrier session has nothing to report a signal
about). It is computed on demand from already-persisted `Feedback` +
`AdaptationResult` + `Barrier` rows — not stored as a second copy of the truth.

This signal is exposed (via the session summary and the Developer Panel) but
**nothing reads it back to change a future decision** — no auto-adaptation
switching, no auto-profile mutation. That boundary is deliberate (section 33): a
future phase, not this one, would build the "learning signal → recommendation
improvement" loop.

## 10. Standard vs. Adaptive comparison & adaptation/barrier effectiveness

`experience_mode` (`"standard"`/`"adaptive"`) is a computed property of the
pre-existing `baseline_mode` boolean, not a new column — `baseline_mode=True` is
already exactly what "standard" means in this codebase (it already powers the
before/after panel), so this phase exposes it under the friendlier name instead
of forking a second field.

`GET /api/analytics/adaptations/` and `.../barriers/` (new) aggregate outcome
evidence per adaptation / per barrier type, each session classified into one of
four states — `positive_observed_outcome`, `negative_observed_outcome`,
`inconclusive`, `insufficient_data` — via documented, centralized thresholds
(`MIN_SESSIONS_FOR_SIGNAL = 3`, completion/assistance/ease floors and ceilings in
`config.py`). Below the minimum sample size, the state is always
`insufficient_data` — this project never claims a pattern from too little
evidence, and the UI always shows the evidence (session count, completion rate,
average ease) alongside the state, never a bare label.

## 11. Privacy

`InteractionEvent.metadata` is capped (10 keys, 200 characters/value) and never
carries raw input — no keystrokes, no audio, no video, no unrelated application
activity. `Feedback.optional_comment` is capped at 500 characters, stored
associated only with the session (never a name or contact detail), not exposed
publicly, and not used for any automatic AI training (there is no AI training
pipeline in this project at all). Every endpoint in this codebase is reachable
anonymously by design (documented in API.md/README as a hackathon-scope choice,
predating this phase) — this phase adds lightweight guards appropriate to that
scope (session-state validation, controlled-vocabulary validation) rather than
building a production authentication/authorization layer, which is explicitly
Phase 8+ territory.

## 12. Analytics architecture

All calculations are centralized in `backend/analytics/services.py` (called
`AnalyticsService` in the spec) — `session_interaction_counts()`,
`calculate_outcome_score()`, `generate_learning_signal()`, `bucket_metrics()`,
`adaptation_effectiveness()`, `barrier_outcomes()`. Views
(`backend/analytics/views.py`) only shape HTTP responses; nothing is duplicated
between a view and a component. Every calculation is a deterministic Django ORM
aggregation — no AI provider is required, and the system behaves identically with
`AI_PROVIDER=none` (the default). `dashboard`/`adaptations`/`barriers`/`sessions`
all return `"empty": true` with no fabricated-zero fields when there is no data
yet (section 39) — the frontend renders "No interaction data yet." rather than a
misleading 0%.

## 13. API endpoints

No existing endpoint's URL changed. New, on the existing `interactions/<id>/...`
family (not a parallel `/api/sessions/...`, since the session-based flow already
lives there): `POST .../events/`, `POST .../complete/`, `POST .../abandon/`.
`POST .../feedback/` gained new optional fields but is fully backward-compatible
(every pre-Phase-7 test and call site still works unchanged). New analytics
endpoints: `GET /api/analytics/adaptations/`, `.../barriers/`, `.../sessions/`.
Full request/response shapes in [API.md](API.md).

## 14. Testing

**50 new backend tests** (187 → 237), full suite **237/237 passing**:

- `feedback/tests.py` — session lifecycle/state-machine (valid/invalid
  transitions, duplicate completion rejected), interaction events (creation,
  invalid event type rejected, batching, metadata sanitization, assistance-count
  increment, no events on a terminal session), feedback validation (ease_rating
  and adaptation_helpfulness controlled vocabularies, comment truncation, second
  submission updates rather than duplicates), and the corrected
  `LearningLoopTests` (profile confidence is now provably *unchanged* by
  feedback).
- `analytics/tests.py` (new file) — outcome score bounds and component behavior,
  learning signal generation (including the "no signal" cases), adaptation/
  barrier effectiveness state thresholds (insufficient/positive/negative/
  inconclusive), and empty-state responses for every analytics endpoint.
- `api/tests.py::Phase7FeedbackAnalyticsAndLearningTests` — full-stack, real
  HTTP-client coverage of the three manual test scenarios below, plus
  authorization-adjacent checks (a completed session can't be completed again —
  409; an invalid event type or ease rating is rejected — 400) and a regression
  canary confirming the Phase 1–6 pipeline this phase builds on still works.
- Frontend: `npx oxlint src` and `npm run build` both clean (this project has no
  Jest/Vitest harness — verification is lint + build + a live Playwright
  walkthrough, consistent with every earlier phase).

## 15. Manual test scenarios (verified live, headless Chromium)

1. **Full completion with feedback** (Low Vision + Reduced Dexterity): start →
   apply → select destination/ticket type → buy → feedback form appears → submit
   (ease 5, helpful "Yes", no assistance) → Outcome Summary shows "Task complete
   ✓"; Developer Panel shows `Outcome: COMPLETED`, a `0.95` outcome score, and a
   `✓ Positive` learning signal.
2. **Abandoned session** (Cognitive Load): start → apply → select a destination →
   use the new "← Back" control → "Leave without finishing" → feedback form still
   appears → submit → Outcome Summary shows "Task not completed"; Developer Panel
   shows `Outcome: ABANDONED` and a `✗ Negative` learning signal (since
   `successful` is false).
3. **Assistance requested** (Hearing Difficulty): start → apply → "Ask staff for
   help" (button becomes "Help requested ✓" and disables, kiosk stays fully
   interactive) → complete the purchase normally → feedback form → submit with
   "Did you need help from another person?" = Yes → Developer Panel's Assistance
   line reads "Yes (1 request)".

All three ran with zero browser console errors and zero failed requests once the
one real bug this phase's own testing caught (below) was fixed.

## 16. A real bug this phase's testing caught and fixed

Live verification against the dev database (not the test suite, which uses an
in-memory database recreated fresh every run) surfaced
`table feedback_interactionsession has no column named assistance_count` — the
new migration existed but had never been applied to the actual `db.sqlite3` file.
Fixed by running `python manage.py migrate` against it; documented here per this
phase's own instruction not to merely report a fixable error.

A second, smaller issue: `DeveloperPanel`'s per-decision "applied to the
interface" text and its Phase 6-added "Applied: ✓" summary both already existed
before this phase but weren't touched — no new bug there. This phase's own new
`Applied`/`Outcome` rendering was verified directly via the live scenarios above.

## 17. Known limitations

- No Jest/Vitest harness — frontend correctness is lint + build + live Playwright,
  not unit tests, matching every earlier phase's approach.
- The outcome-score weights and effectiveness thresholds in `analytics/config.py`
  are reasonable, documented, hackathon-scope defaults — not empirically tuned
  against real accessibility research.
- `time_penalty` never applies in the current demo (the seeded task defines no
  `time_limit_seconds`) — the mechanism exists and is tested, but isn't visible
  without seeding a task that sets one.
- No production authentication/authorization — consistent with this project's
  existing, documented "no real user account system" limitation; Phase 7 adds
  state-machine and controlled-vocabulary validation, not user-identity
  enforcement.

## 18. Phase 8 boundary

Nothing in this phase closes the loop back to Phase 5. The Learning Signal is
exposed as evidence — in the session summary and the Developer Panel — and
nowhere consumed to auto-select a different adaptation or auto-edit an Ability
Profile dimension's level. **Phase 7 measures the outcome of adaptations. It does
not diagnose users or automatically modify their ability profile.** Building the
"Learning Signal → Recommendation Improvement" loop itself, along with production
deployment, advanced security hardening, Docker production setup, IoT/wearable/
OS-level integration, a developer SDK, production monitoring, or advanced ML
recommendation models, is explicitly out of scope here — Phase 8+ territory.
