# Profile 9 — High Interaction Sensitivity

> **Naming note:** same convention as `docs/PROFILE_8_VISUAL_HEARING_SUPPORT.md`
> — this is "Phase 6," the **final** phase of the separate "add demo
> profiles 4–9" initiative, not this project's original Phases 1–8
> (`docs/PHASES.md`). Named by profile, not by phase number, to avoid any
> collision. **This is the last planned demo persona — no Profile 10.**

## Objective

Add the ninth and final working demo profile — **High Interaction
Sensitivity** — fully integrated through the existing pipeline, reusing the
same `purchase_ticket` task and `kiosk_standard` environment every other
profile uses. No new architecture, no duplicated engines.

## Product principle

"High Interaction Sensitivity" represents a person who benefits from stable,
predictable, deliberate interaction — clearly separated controls and a
confirmation step before a consequential action — reducing (not
guaranteeing the prevention of) accidental or unintended activation. A
**functional** interaction preference, never a medical or psychological
diagnosis; no clinical terminology or severity scale is used anywhere.

## Key finding before writing any code

No existing ability dimension represents interaction sensitivity, and no
existing barrier represents either of this profile's two concerns (control
spacing, or a consequential action with no confirmation step):
`small_tap_targets` is about control *size*, not the *gap* between
controls; `too_many_choices` is about *count*, not proximity; nothing
currently treats "missing confirmation" as a barrier at all — it has only
ever been an adaptation effect. A new dimension and a new barrier were
therefore genuinely necessary — but **zero new adaptations** were: both
`increase_spacing` and `confirmation_before_irreversible_action` already
exist and are directly, honestly relevant.

## New ability dimension: `interaction_sensitivity`

Added to `abilities/constants.py`'s `DIMENSION_KEYS`/`ALLOWED_LEVELS` —
the same controlled-vocabulary architecture every other dimension uses, so
`abilities/services/profile_service.py`'s validation, `AbilityProfile.
dimension()`'s fallback, and the frontend's editable profile form all
support it with **zero additional code**, purely by extending the shared
constants both layers already read from generically.

Deliberately a **2-value** vocabulary (`typical`, `high`), not the usual
3-tier shape — this profile is functional/binary ("benefits from more
deliberate interaction" or not), not a severity scale.

The 8 pre-existing demo profiles were **not** retroactively edited to add
an explicit `interaction_sensitivity: typical` entry — both engines'
`_dimension()` helpers already default a missing key to `{"level":
"typical", ...}`, so this is a safe, zero-behavior-change omission (verified
live: Cognitive Load, which has several other non-typical dimensions, still
produces no `accidental_activation_risk` barrier). Touching all 8 existing
profile dicts for a value that changes nothing would have been exactly the
kind of unrelated-functionality edit this phase's instructions warned
against.

## New barrier: `accidental_activation_risk`

Added to `Barrier.TYPE_CHOICES`, implemented in both engines. Named after
one of the request's own suggested terms, broad enough to honestly cover
both of the profile's distinct real causes (Section 7 frames the whole
profile around one umbrella concept, "unintended/accidental interaction" —
implemented as one barrier type, not two, matching "only add a new barrier
if genuinely necessary" and avoiding an artificially narrow name).

**Trigger** (either cause alone is sufficient; both together raise
severity): `interaction_sensitivity: high`, **and**
- adjacent controls are closer than `SAFE_CONTROL_SEPARATION_PX` (32px,
  documented in `detection.py`/`config.py`), measured via a new environment
  fact `min_control_spacing_px` — **not** a fabricated number:
  `kiosk_standard.json`'s real tightest existing gap (the `ticket_single`/
  `ticket_return` pair) is 20px, so the fact simply states what was already
  true of the fixture; **and/or**
- the consequential action lacks a confirmation step, via a new environment
  fact `confirmation_available` (honestly `false` in both fixtures — no
  environment in this codebase has ever baked in confirmation; it has only
  ever existed as an adaptation effect).

**Live evidence example** (both causes present, verified against a real
session):
```
For a 'high' interaction-sensitivity profile, adjacent controls are only
20px apart, below the 32px comfortable separation and the consequential
action (purchase) completes on a single tap with no confirmation step.
```

Verified negative in every direction the request required: a typical-
sensitivity profile against the same crowded/unconfirmed environment
detects nothing; a high-sensitivity profile against a well-separated,
already-confirmed environment detects nothing; either cause **alone**
(good spacing + no confirmation, or tight spacing + confirmation present)
still correctly detects the barrier in isolation, with severity scaling by
how many distinct causes are present (0.60 for one cause, 0.75 for both).

## Adaptations: `increase_spacing` (primary) + `confirmation_before_irreversible_action` (secondary) — both reused

`increase_spacing`'s own pre-existing description — *"Adds space between
controls to reduce accidental adjacent taps"* — already named exactly this
barrier's concern before this phase existed. Its `resolves_barrier_types`
was extended to include `accidental_activation_risk`; the same was done for
`confirmation_before_irreversible_action`, following the established
secondary-candidate pattern from Phases 2–4. Verified live via the scoring
engine: `increase_spacing` scores 2.29 vs. `confirmation_before_irreversible
_action`'s 2.01 for the same barrier — an engine-driven outcome.

## Safety

Zero new allowlist entries — `spacing_scale` and `confirm_step` were both
already approved `ui_effects` keys from earlier phases. Both validators
remain fully generic.

## Adaptive kiosk

No `KioskView.jsx` changes were needed. `--spacing-scale` already drives
every gap in the kiosk (`.kiosk__body`, `.kiosk__grid`, `.kiosk__quantity`)
generically from `appliedEffects.spacing_scale`, and the confirmation dialog
(`confirmingPurchase`) already renders generically from `appliedEffects.
confirm_step` — both pre-existing, profile-agnostic mechanisms from earlier
phases. Applying `increase_spacing` genuinely widens every control gap in
the kiosk by 1.6x, a real, visible, verified-live layout change.

## Event tracking, feedback, learning signal, analytics

No changes needed — all already fully generic over
`(adaptation_id, barrier_type, task_id)`. No new event type was added (the
existing `control_selected`/`confirmation_opened`/`confirmation_completed`
events already capture everything relevant to this profile's journey).

## Testing

**13 new backend tests**, full suite **310/310 passing**:
- `barriers/tests.py` (live engine): all 4 of Section 20's numbered
  scenarios (crowded, missing-confirmation-alone, both-resolved, typical
  profile), plus the "no spacing fact at all" edge case.
- `barriers/test_rules.py` (standalone engine): the same coverage for
  `AccidentalActivationRiskRule`, plus a check that two simultaneous causes
  score strictly higher than one.
- `api/tests.py`: a full-stack test mirroring the eight existing persona
  tests, plus an explicit negative-case test.

**Live verification** (Playwright): the new profile's complete journey
(barrier detected, `increase_spacing` applied, wider control gaps visibly
rendered, purchase completed); a regression pass on Low Vision (which also
uses `spacing_scale` via a *different* adaptation, `increase_target_size` —
confirmed unaffected) and Slower Reaction Speed. Zero browser console
errors.

## Regression confirmation

All eight existing profiles verified still fully functional via the full
automated suite (310/310); Low Vision and Slower Reaction Speed also
re-run live end-to-end this phase. No existing barrier, adaptation, or
fixture field was modified — only additive facts and extended
`resolves_barrier_types` lists.

## Demo steps

1. `python manage.py seed_demo` (idempotent).
2. Explore AbilityOS → select **High Interaction Sensitivity** → Consent →
   Save Profile → Continue to Task & Environment.
3. Analyze Task → Analyze Environment → Detect Barriers (shows *"Accidental
   activation risk"*) → Recommend Adaptation (shows *"Increase spacing"*) →
   Open Adaptive Kiosk.
4. Start Ticket Purchase — note the standard control spacing. Apply
   Approved Adaptation(s) — every control gap visibly widens.
5. Complete the purchase, submit feedback, and check the Developer Panel's
   glance strip and the Analytics dashboard.

---

**Profile 9 implemented end-to-end. This is the final planned AbilityOS
demo persona — no Profile 10 was added.**
