# Profile 7 — Slower Reaction Speed

> **Naming note:** same convention as `docs/PROFILE_6_FATIGUE_REDUCED_STAMINA.md`
> — this is "Phase 4" of the separate, new "add demo profiles 4–9"
> initiative, not this project's original Phases 1–8 (`docs/PHASES.md`).
> Named by profile, not by phase number, to avoid any collision.

## Objective

Add a seventh working demo profile — **Slower Reaction Speed** — fully
integrated through the existing pipeline, reusing the same `purchase_ticket`
task and `kiosk_standard` environment every other profile uses. No new
architecture, no duplicated engines, no profiles 8–9.

## Product principle

"Slower Reaction Speed" is a **functional interaction requirement**, not a
medical diagnosis: *"rapid interactions or disappearing prompts can be
difficult."* The system identifies a mismatch between the user's
response-time requirement and the kiosk's response-time demand — never a
diagnosis of slow reaction time.

## Profile

- **Label:** Slower Reaction Speed · **Username:** `demo_slower_reaction_speed`
- **Primary dimension:** `reaction_speed: slower` (confidence 0.8,
  `source: manual`) — reused directly from `abilities/constants.py`'s
  existing `["typical", "slower", "needs-extended-time"]` vocabulary, already
  in use (at `slower`, confidence 0.6) by the pre-existing Cognitive Load
  persona as a secondary trait.
- **`preferred_modality`:** `visual`.

**Card copy** — `SUMMARY_COPY.reaction_speed.slower` already existed,
unedited, and reads *"A little extra time helps."* — matching the requested
first bullet almost verbatim; `preferred_modality: visual` supplies the
second bullet. As with every prior profile, the middle requested sentiment
("rapid interactions... can be difficult") isn't a separate card bullet —
it appears instead as the barrier's own evidence text, a fact about *this
environment's* timing demand, not a general profile trait.

## Key finding before writing any code

No timing metadata existed anywhere in the repository — no timeout,
countdown, response-window, or confirmation-expiration concept in any model,
fixture, or barrier/adaptation. This phase's timing mechanism is genuinely
new, not a reuse of something already there (confirmed by inspection of
`detection.py`, `rules.py`, both environment fixtures, `feedback/models.py`'s
event types, and `TASK_STEPS`).

A second finding, confirmed by direct code reading: `detect_barriers()`'s
`task_descriptor` parameter is never actually read by any existing rule in
the live engine — the live pipeline always calls it with only
`{"task_id": ...}`. This is the same reason Phase 3's `interaction_step_count`
was modeled as an **environment** fact rather than a task fact; the same
reasoning applies here: `confirmation_timeout_seconds` is added as a new,
additive, top-level fact on both environment fixtures (not a new,
parallel timing system on the task or on individual controls — the smallest
single fact needed, per the request's explicit "do not invent multiple
thresholds" instruction).

## New barrier: `time_limited_interaction`

Added to `Barrier.TYPE_CHOICES`, implemented in both existing engines (live
`detection.py`, standalone `rules.py`) — the same "two engines, one barrier
type" pattern every prior profile phase established.

**Trigger:** `reaction_speed` level is `slower` or `needs-extended-time`
(not `typical`), **and** the environment's `confirmation_timeout_seconds` is
strictly below the profile's configured required response window. The
required-response thresholds are a single, explicit, documented dict (not
scattered/invented per-call):
```python
REQUIRED_RESPONSE_SECONDS = {"typical": 5, "slower": 10, "needs-extended-time": 15}
```
`typical`'s requirement is deliberately set equal to the standard kiosk's own
5-second window, so a typical profile can never trigger a mismatch against
it by construction — the same "baseline never triggers" principle every
other severity dict in this codebase already follows.

**Live evidence example** (verified against a real session):
```
The purchase confirmation provides only a 5-second response window, below
the 10-second response-time requirement configured for a 'slower'
reaction-speed profile.
```

This is a genuine `PROFILE + ENVIRONMENT → MISMATCH` check, not
`if profile == slower_reaction_speed`: verified directly (both automated
tests and a live shell check) across all four of the request's mandated
negative-case scenarios:
1. Typical reaction speed + 5-second timeout → no barrier.
2. Slower reaction speed + 5-second timeout → barrier (severity 0.8).
3. Slower reaction speed + a generous 30-second timeout → no barrier.
4. Slower reaction speed (10-second requirement) against an environment
   configured with *exactly* 10 seconds → no mismatch (a boundary case,
   `<` not `<=`).

## Environment metadata added (both fixtures, additive only)

One new top-level fact, `"confirmation_timeout_seconds": 5`, added to both
`backend/fixtures/kiosk_standard.json` and
`backend/environments/fixtures/ticket_kiosk_default.json` — no existing
field touched. This single fact is the entire timing model; no per-control
duplicate timing field was added (the request explicitly warned against
inventing multiple timing systems).

## New adaptation: `increase_interaction_timeout`

Checked the existing catalogue first, per the request. No existing
adaptation extends response time; `confirmation_before_irreversible_action`
(a deliberate "are you sure?" pause) was identified as a real, if imperfect,
**secondary candidate** — it doesn't extend the timer, but it is a genuine
second look before an irreversible action — and its `resolves_barrier_types`
was extended to include `time_limited_interaction`, following the exact
established pattern from Phases 2/3. Verified live via the scoring engine:
`increase_interaction_timeout` scores 2.66 vs.
`confirmation_before_irreversible_action`'s 2.02 for the same barrier — an
engine-driven outcome, not hardcoded.

Added to the shared `Adaptation` catalogue (17 entries now):
```python
dict(
    name="increase_interaction_timeout",
    display_name="Increase interaction timeout",
    resolves_barrier_types=["time_limited_interaction"],
    modality="visual",
    accessibility_benefit=0.9, interaction_cost=0.10, risk=0.05,
    risk_level=Adaptation.RISK_LOW,
    ui_effects={"extended_timeout_seconds": 20},
)
```
The extended value (20 seconds) is a real, configured number the frontend
actually uses to run its countdown — never a hardcoded UI string.

## Safety

One new allowlist entry: `"extended_timeout_seconds"` added to
`ALLOWED_UI_EFFECT_KEYS` (`backend/adaptations/services/config.py`). Both
safety validators remain fully generic/data-driven; no bespoke rule was
needed. Verified live: the candidate is scored, approved by the rule engine,
and never bypasses validation.

## Adaptive kiosk — a real, functional countdown (not faked)

`KioskView.jsx`'s confirmation screen now runs a genuine `setInterval`-driven
countdown, not a static "04 seconds" string:
- The countdown starts once the confirm screen becomes the active,
  actionable step (destination + ticket type already chosen) and ticks down
  once per real second.
- **Standard:** *"Please confirm within 5 seconds."* with a live ticking
  number. If it reaches 0 before BUY TICKET is tapped, the interaction
  genuinely expires — BUY TICKET is removed and replaced with *"⏱ Time
  expired. Please try again."* and a **Try Again** button that restarts a
  fresh countdown (the person is never stuck; this is a real recovery path,
  not an abandoned task).
- **Adaptive** (once `increase_interaction_timeout` is applied): *"Take your
  time to review."* with the same live countdown, now starting from the real
  extended value (20 seconds) read from `ui_effects.extended_timeout_seconds`.

Verified live via Playwright: a standard-mode session was left untouched for
6 real seconds and genuinely showed the expired state and recovered via Try
Again; an adaptive-mode session showed the extended countdown and completed
normally.

## Task logic unchanged

The four required steps (destination, ticket type, quantity, confirm) are
untouched. The adaptation only changes **how much time** the person has to
respond at the confirmation step — never which steps exist or what
information is required.

## Event tracking, feedback, learning signal

One new, minimal event type was added — `interaction_timeout`
(`feedback/models.py`) — fired only when a standard-mode countdown actually
reaches zero, observable in the session exactly like every other event.
`analytics.services.session_interaction_counts()` gained a `timeouts_count`
field alongside the existing `errors_count`/`retries_count`/
`backtracks_count`, reusing the exact same aggregation pattern (no new
metrics system). `InteractionSession`, `Feedback`, and
`generate_learning_signal()` needed no changes — already fully generic over
`(adaptation_id, barrier_type, task_id)`.

## A note on Cognitive Load (pre-existing persona, not modified)

The Cognitive Load persona already had `reaction_speed: slower` (confidence
0.6) since the original build, unrelated to this phase. Once the new
environment fact and barrier existed, it legitimately started producing
`time_limited_interaction` too, alongside its pre-existing barriers — the
same kind of honest co-firing Phase 3 already established with
`fatigue_degraded_precision`. The live session pipeline applies all four
resulting adaptations together with no conflict (`increase_interaction_
timeout`'s `extended_timeout_seconds` key doesn't collide with any other
applied adaptation's keys, unlike Phase 3's `flow` collision). The
standalone Task & Environment demo screen's single-best-pick endpoint now
reasonably selects `increase_interaction_timeout` as Cognitive Load's single
strongest candidate overall (lower cost/risk than the choice-related
options) — a pre-existing test in `adaptations/test_recommender.py` asserted
a fixed set of expected picks for that endpoint and was updated to include
this new, legitimate outcome, with the reasoning documented inline. Nothing
about Cognitive Load's actual behavior regressed: `step_by_step_flow` is
still recommended and still applied in the real kiosk session.

## Testing

**14 new backend tests**, full suite **291/291 passing**:
- `barriers/tests.py` (live engine): the four mandated Step 26 scenarios,
  plus a regression guard against `STANDARD_KIOSK_ENV` (no
  `confirmation_timeout_seconds` fact).
- `barriers/test_rules.py` (standalone engine): the same coverage for
  `TimeLimitedInteractionRule`, plus `needs-extended-time` and the
  evidence-field check.
- `api/tests.py`: a full-stack test mirroring the six existing persona
  tests, plus an explicit negative-case test.
- `adaptations/test_recommender.py`: one pre-existing test updated (see
  above), not removed or weakened — its actual intent (Cognitive Load gets a
  sensible adaptation) still holds.

**Live verification** (Playwright): the new profile's complete journey
(extended countdown, successful completion); a dedicated scenario that
deliberately waits 6 real seconds on a standard (non-extended) confirmation
screen and confirms the timeout genuinely fires and recovers via Try Again;
regression passes on Cognitive Load and Speech Difficulty. Zero browser
console errors throughout.

## Regression confirmation

All six existing profiles verified still fully functional via the full
automated suite (291/291); Cognitive Load and Speech Difficulty also
re-run live end-to-end this phase. No existing barrier, adaptation, or
fixture field was modified — only additive facts, one new rule/adaptation,
and one pre-existing test's expected-outcome set updated to reflect a
legitimate new finding.

## Demo steps

1. `python manage.py seed_demo` (idempotent).
2. Explore AbilityOS → select **Slower Reaction Speed** → Consent → Save
   Profile → Continue to Task & Environment.
3. Analyze Task → Analyze Environment → Detect Barriers (shows *"Time-limited
   interaction"*) → Recommend Adaptation (shows *"Increase interaction
   timeout"*) → Open Adaptive Kiosk.
4. Start Ticket Purchase, select a destination and ticket type to reach the
   confirmation screen — note the real countdown reads *"Take your time to
   review."* starting at 19–20 seconds (vs. the standard 5-second window a
   typical profile would see on the same kiosk).
5. Complete the purchase, submit feedback, and check the Developer Panel's
   glance strip and the Analytics dashboard.
