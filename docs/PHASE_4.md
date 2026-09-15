# Phase 4 — Barrier Detection Engine

## Purpose

Phase 4 answers exactly one question:

> "What specific mismatch between this person's functional ability and the
> demands of this task/environment could make the task difficult?"

It never answers "how should we fix it?" — a `BarrierResult` has no
`adaptation`/`recommended_action`/`solution`/`fix` field, and every rule's
unit tests assert none of those words appear anywhere in its output.
Choosing an intervention is a later phase's job.

## Architecture

```
AbilityProfile.dimensions (dict)
TaskDescriptor            (dict, from tasks.services.task_service — Phase 3)
EnvironmentDescriptor     (dict, from environments.services.analyzer — Phase 3)
            │
            ▼
   BarrierDetectionService.detect(profile, task, environment)
            │
            ▼
      BARRIER_RULES  (barriers/services/rules.py)
        ├── SmallTapTargetRule
        ├── LowContrastTextRule
        ├── TooManyChoicesRule
        └── AudioOnlyAlertRule
            │
            ▼
      list[BarrierResult]  (severity-sorted, deduplicated)
```

Every rule is a plain Python class operating on three dicts — no Django
model access, no HTTP request object, no database query. This is what
makes `barriers/test_rules.py` able to unit-test a rule directly, in
isolation, without spinning up an API client (Phase 4 spec section 15).

Thresholds live in one place, `barriers/services/config.py`, each with a
comment explaining *why* that number and not another — not scattered
magic numbers.

## The four rules

| Barrier type | Ability dimension | Trigger levels | Threshold |
|---|---|---|---|
| `small_tap_targets` | dexterity | `reduced-precision`, `single-tap-only` | 160×48px |
| `low_contrast_text` | vision | `low-contrast-sensitive` | 4.5:1 (WCAG AA) |
| `too_many_choices` | cognition | `prefers-fewer-choices`, `needs-step-by-step` | 4 simultaneous choices |
| `audio_only_alert` | hearing | `partial`, `relies-on-visual` | any critical audio-only alert |

`low_contrast_text` deliberately triggers only on `low-contrast-sensitive`,
not `large-text-needed` — contrast and text size are different concerns
the spec's own rule 10 keeps separate, even though the pre-existing
session-based detector (built earlier, still powering the real kiosk)
historically conflated them. The two engines are allowed to differ here;
see "Two barrier engines" below.

Severity formulas (documented in full in `rules.py`'s docstrings/comments):
a base severity from how severe the ability limitation itself is, scaled
toward 1.0 by how far the measured fact falls below its threshold — never
an arbitrary or random number, always reproducible from the same inputs.

Confidence is the Ability Profile's own stated confidence for that
dimension (or a reduced ceiling when a rule had to fall back to a
qualitative signal instead of a precise measurement) — not a fabricated
statistical certainty for a deterministic rule (spec section 6).

## Fifth rule deferred: `fatigue_related_load`

Not implemented. It requires a live fatigue *signal* distinct from the
stored baseline profile — the spec's own example is a session's error rate
climbing over time. This standalone, session-independent engine has no
such session-derived signal available to it. Implementing it against the
static baseline alone would just restate the dexterity/cognition rules
under a different name. Deferred until a real signal exists.

## Task ↔ Environment control matching

`_task_relevant_controls()` in `rules.py` matches environment controls to
the task's own control ids, evaluating only controls relevant to the task
(spec section 24) — falling back to every environment control if the two
happen to share no ids (a real situation this repo had: `ticket_kiosk_default`
and `purchase_ticket` were built independently in Phase 3 with non-
overlapping illustrative ids). Rather than leave that silently broken,
`ticket_kiosk_default.json` was additively enriched with entries under the
task's *real* control ids (`buy_ticket`, `dest_central_station`,
`ticket_single`) — nothing renamed or removed, matching what was already
approved in Phase 3.

## Two barrier engines, on purpose

This repo has **two** barrier detectors, and that's deliberate, not
duplication:

- `barriers/services/detection.py` — pre-existing (built before this
  phase-gated process began), tightly coupled to `InteractionSession`,
  powers the real, working, already-demoed kiosk pipeline. **Untouched.**
- `barriers/services/{config,result,rules,detector}.py` — this phase's new
  work: standalone, class-based, rule-registry architecture exactly
  matching this phase's spec, driving the new Task & Environment screen's
  "Barrier Analysis" section.

They necessarily use different environment fixtures too (`kiosk_standard`
vs `ticket_kiosk_default`) for the reasons documented in
[PHASE_3.md](PHASE_3.md). Consolidating them into one engine is future
work, not something this phase's instructions asked for or something that
could be done without touching the pre-existing, already-approved pipeline.

## API

`POST /api/barriers/detect/` — extended (same pattern as Phase 3's
`/api/environment/analyze/`) to accept `{"user_id", "task_id",
"environment_id"}` with no session, alongside its existing `{"session_id"}`
form. See [API.md](API.md) for the full contract, including the `403` when
consent hasn't been granted.

## Testing

`barriers/test_rules.py` — 53 tests: all 20 rule-level cases from spec
section 31 (small-tap-targets ×8, low-contrast ×4, too-many-choices ×4 [+1
fallback], audio-only ×4), the `BarrierDetectionService` integration tests
(profile-dependency, task-dependency, determinism, dedup/sort, "never
contains an adaptation field"), the full API integration test against the
real seeded demo scenario, and a `RegressionTests` class re-verifying every
Phase 1/2/3 endpoint plus the pre-existing session-based barrier flow.
**147/147 tests pass** across the whole project after this phase.

## Frontend

`TaskEnvironmentPage.jsx`'s "Barrier Analysis" section (replacing Phase
3's "Coming in Phase 4" placeholder, now that Phase 4 exists) — a
`[Detect Barriers]` button, then one `BarrierCard` per detected barrier:
title, ability dimension, a severity bar, the human-readable description,
and an expandable "Why was this detected?" panel tracing Ability →
Environment fact → Rule → Result → Confidence. No kiosk UI, no button
sizes, no contrast, no flow was changed by this phase — `KioskView.jsx`
and `DemoPage.jsx` are untouched.

## Explicit limitations (by design, this phase)

- Deterministic only — no LLM, no ML, no computer vision, no randomness.
- Only 4 of the 5 documented barrier types are implemented;
  `fatigue_related_load` is explicitly deferred (no real signal to detect
  it from yet).
- No adaptation, recommendation, scoring, or safety-approval logic exists
  in this phase's new code path.
- The new standalone engine does not persist `Barrier` rows to the
  database — it's a stateless "what would be detected" query, matching the
  Phase 3 analyze endpoints' pattern. The pre-existing session-based
  detector still does persist, for the real kiosk pipeline.

## Ready for Phase 5

`BarrierDetectionService.detect()` returns exactly `List[Barrier]` —
`barrier_type`, `ability_dimension`, `severity`, `confidence`, `evidence` —
everything an Adaptation Decision engine needs to rank candidate
interventions per barrier, without this phase having decided anything
about what those interventions should be.
