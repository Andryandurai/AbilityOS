# Profile 4 — Limited Mobility + Reach

> **Naming note:** the request that produced this document called itself
> "Phase 1 of a 6-phase implementation" — that numbering is a separate,
> new initiative (adding demo profiles 4–9) and is **not** the same
> sequence as this project's existing Phases 1–8 (Foundation through
> Hardening/Deployment Readiness, documented in `docs/PHASES.md`). This file
> is deliberately not named `PHASE_1.md` to avoid colliding with that
> existing, unrelated Phase 1 (Foundation).

## Objective

Add a fourth working demo profile — **Limited Mobility + Reach** — fully
integrated through the existing pipeline (Ability Profile → Task →
Environment → Barrier Detection → Adaptation Decision → Safety Validation →
Adaptive Kiosk → Completion → Feedback → Learning Signal), reusing the same
`purchase_ticket` task and `kiosk_standard` environment every other profile
uses. No new architecture, no duplicated engines, no profiles 5–9.

## Profile

- **Label:** Limited Mobility + Reach
- **Username:** `demo_limited_mobility_reach`
- **Primary dimensions:** `reach: seated` (confidence 0.82), `mobility: limited`
  (confidence 0.78), both `source: manual` — the same controlled vocabulary
  every other demo profile uses (`backend/abilities/constants.py`), not a
  new value invented for this profile.
- **`preferred_modality`:** `visual`.

**Card copy** (`frontend/src/constants/abilityProfile.js`'s `SUMMARY_COPY`,
already existed unused since Phase 2 — this profile is the first to actually
exercise it):
> AbilityOS understands:
> - Seated interaction works best for you. *(from `reach: seated`)*
> - Important controls should stay within a comfortable interaction area.
>   *(from `mobility: limited`)*
> - Visual interaction is preferred. *(from `preferred_modality: visual`)*

The requested third bullet, *"Reaching toward distant controls can be
difficult,"* is not a separate profile-summary bullet — this codebase's
existing summarization architecture (`summarizeProfile()`) renders exactly
one bullet per non-baseline dimension, and `reach` can only be at one level
at a time. That exact sentiment appears instead, verbatim in spirit, as the
barrier's own evidence text below — arguably the more correct home for it,
since it's a fact about *this environment*, not a general profile trait.

## New barrier: `controls_out_of_reach`

Added to `Barrier.TYPE_CHOICES` (`backend/barriers/models.py`) alongside the
five existing types — no renaming, no removal.

**Trigger:** `reach` level is `limited-upper` or `seated` (not `full`), **and**
a task-relevant control's position falls outside the environment's
`interaction_zone`. Severity: `limited-upper` → 0.55, `seated` → 0.8 —
mirroring every other rule's `{level: severity}` dict pattern in this file.

**Live evidence example** (from `backend/barriers/services/detection.py`,
verified against a real session):
```
Primary control 'buy_ticket' is positioned at (1100, 60), outside the
configured comfortable interaction zone (x:40-540, y:420-720) for a
'seated' reach profile.
```

This is deterministic and relational — `PROFILE + ENVIRONMENT`, not
`PROFILE = BARRIER` — implemented identically to every existing rule.

### Two engines, one barrier type (existing architecture, reused)

This codebase has two barrier-detection engines by design (documented in
`docs/PHASE_7.md`/`details.md`): the **live** engine
(`barriers/services/detection.py`), which powers the real kiosk, and the
**standalone** engine (`barriers/services/rules.py`), which powers the
Task & Environment demo screen's own "Detect Barriers" button. Both needed
this rule, so both got it — `controls_out_of_reach` is implemented in each,
using each engine's own established style (a plain `if`-based check in the
live engine; a `BarrierRule` subclass registered in `BARRIER_RULES` in the
standalone one), matching how every other barrier type is already handled
in both places.

## Environment metadata added (both fixtures, additive only)

Neither fixture's existing control widths/heights/labels/ids were touched —
only new fields were added, so every barrier this depends on continues
working unchanged.

- **`backend/fixtures/kiosk_standard.json`** (live kiosk): added `x`/`y` to
  every control (previously had none), and a top-level
  `"interaction_zone": {"x": 40, "y": 420, "width": 500, "height": 300}` — a
  lower band of the 1280×800 screen, representing a seated person's
  comfortable reach. `buy_ticket` (the task's `primary: true` control) is
  positioned at `(1100, 60)` — outside that zone, representing a real,
  documented accessibility problem (a payment/confirm control mounted too
  high for a seated/wheelchair user).
- **`backend/environments/fixtures/ticket_kiosk_default.json`** (the
  standalone Phase 3/4 demo fixture): already had `x`/`y` per control from
  Phase 3 — only `"interaction_zone": {"x": 20, "y": 20, "width": 300,
  "height": 300}` was added (a small top-left band); the existing
  `buy_ticket` control at `(100, 500)` was never touched and simply already
  falls outside this zone.

These `x`/`y`/`interaction_zone` facts feed barrier *detection* only — they
are not literally read by the kiosk's CSS layout (which remains a simple
vertical stack, as documented in `docs/PHASE_6.md`); the kiosk's own visual
"reach zone" effect (below) is a separate, deliberate simulation of what the
detected mismatch means, exactly the same relationship the existing
tap-target-size barrier has to the kiosk's "missed tap" simulation.

## New adaptation: `reachable_control_layout`

Added to the **existing, shared** `Adaptation` catalogue (13 entries now) via
`seed_demo.py` — reuses the same table both barrier-detection engines and
both safety validators already read; no second catalogue.

```python
dict(
    name="reachable_control_layout",
    display_name="Reachable control layout",
    resolves_barrier_types=["controls_out_of_reach"],
    modality="visual",
    accessibility_benefit=0.9, interaction_cost=0.15, risk=0.05,
    risk_level=Adaptation.RISK_LOW,
    ui_effects={"reachable_layout": True},
)
```

No secondary adaptations (`simplify_navigation`, `alternative_voice_input`,
etc.) were made to resolve this barrier — they address different mismatches
entirely, and attaching them here would have been exactly the kind of
"unrelated adaptation" the request explicitly warned against.

## Safety

The **only** safety-layer change required was adding `"reachable_layout"` to
`ALLOWED_UI_EFFECT_KEYS` (`backend/adaptations/services/config.py`) — both
the live validator (`adaptations/services/rules.py`) and the standalone
9-rule validator (`adaptations/services/validator.py`) are fully generic and
data-driven; neither needed a bespoke new rule. Verified live: the candidate
is scored (2.63–2.76 depending on the exact session), approved by the rule
engine, and never bypasses validation — same pipeline every other profile
uses.

## Adaptive kiosk

`frontend/src/components/KioskView.jsx` reads the new `reachable_layout`
`ui_effects` key (added to the existing fixed-vocabulary reader, same
pattern as every other key). Before the adaptation is applied, the BUY
TICKET section is visually pushed out of the normal flow with a dashed
warning border and the text *"⚠ This control is outside the comfortable
interaction area."* — after it's applied, the same section is pulled back
into a highlighted, labeled zone: *"✓ Positioned within the comfortable
interaction area."* A real, visible layout change — not a label claiming
one happened — verified live via Playwright screenshots before/after
applying.

## Task completion, feedback, learning signal

No changes were needed anywhere in this layer — `InteractionSession`,
`InteractionEvent`, `Feedback`, and `analytics.services.generate_learning_signal()`
are all already fully generic over `(adaptation_id, barrier_type, task_id)`.
Verified live: completing a purchase with this profile applied produces
`applied_adaptations: ["reachable_control_layout"]`, a positive learning
signal (*"reachable_control_layout resolved controls_out_of_reach for
purchase_ticket"*), and the session correctly feeds the Analytics
dashboard's "With AbilityOS" bucket.

## Testing

**10 new backend tests**, full suite **255/255 passing**:
- `barriers/tests.py` (live engine): the new rule triggers for
  `seated`/positioned-outside-zone, doesn't trigger for `typical` reach or a
  control already inside the zone, and — a regression guard — stays a true
  no-op against the shared `STANDARD_KIOSK_ENV` fixture every other test in
  that file uses (which has no `x`/`y`/`interaction_zone`).
- `barriers/test_rules.py` (standalone engine): the same coverage for
  `ControlsOutOfReachRule`, plus `limited-upper` reach and a
  no-`interaction_zone` no-op case.
- `api/tests.py`: a full-stack test mirroring the existing three persona
  tests exactly — start → analyze → detect → recommend → apply against the
  real session-based API, asserting `controls_out_of_reach` is detected and
  `reachable_control_layout` is applied.

**Live verification** (Playwright, headless Chromium): the full journey —
Select → Consent → Profile → Summary → Analyze Task/Environment → Detect
Barriers → Recommend Adaptation → Open Adaptive Kiosk → Apply → complete a
purchase → Feedback → Outcome — for the new profile, plus a regression pass
re-running the same flow for all three existing profiles. **Zero browser
console errors** across all four. The Developer Panel's Phase 8 "at a
glance" strip correctly showed `WHY: Controls outside comfortable reach` →
`CHANGE: Reachable control layout` → `RESULT: Completed independently`.

## Regression confirmation

All three existing profiles verified unchanged and still fully functional:
Low Vision + Reduced Dexterity (`small_tap_targets` → `increase_target_size`),
Hearing Difficulty (`audio_only_alert` → `caption_audio`), Cognitive Load
(`too_many_choices` → `step_by_step_flow`). Every pre-existing backend test
(245 of them) still passes unmodified.

## Demo steps

1. `python manage.py seed_demo` (idempotent — safe to re-run; creates the new
   profile and the 13th adaptation on top of whatever already exists).
2. Explore AbilityOS → select **Limited Mobility + Reach** → agree to
   consent → Save Profile → Continue to Task & Environment.
3. Analyze Task → Analyze Environment → Detect Barriers (shows *"Controls
   outside comfortable reach"*) → Recommend Adaptation (shows *"Reachable
   control layout"*) → Open Adaptive Kiosk.
4. Start Ticket Purchase — note the BUY TICKET button's dashed warning
   border. Apply Approved Adaptation(s) — the button visibly moves into the
   highlighted "within reach" zone.
5. Complete the purchase, submit feedback, and check the Developer Panel's
   glance strip and the Analytics dashboard.
