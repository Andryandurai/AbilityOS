# Profile 6 — Fatigue / Reduced Stamina

> **Naming note:** same convention as `docs/PROFILE_4_LIMITED_MOBILITY_REACH.md`
> and `docs/PROFILE_5_SPEECH_DIFFICULTY.md` — this is "Phase 3" of the
> separate, new "add demo profiles 4–9" initiative, not this project's
> original Phases 1–8 (`docs/PHASES.md`). Named by profile, not by phase
> number, to avoid any collision.

## Objective

Add a sixth working demo profile — **Fatigue / Reduced Stamina** — fully
integrated through the existing pipeline, reusing the same `purchase_ticket`
task and `kiosk_standard` environment every other profile uses. No new
architecture, no duplicated engines, no profiles 7–9.

## Product principle

"Fatigue / Reduced Stamina" is a **functional interaction requirement**, not
a medical diagnosis: *"extended or repetitive interaction can increase task
difficulty."* The system prefers a lighter interaction flow — fewer
navigation transitions and less repeated tapping — over a longer one. No
diagnostic or medical language ("medically fatigued", "fatigue disorder")
appears anywhere in the implementation.

## Profile

- **Label:** Fatigue / Reduced Stamina · **Username:** `demo_fatigue_reduced_stamina`
- **Primary dimension:** `fatigue: high` (confidence 0.8, `source: manual`) —
  reused directly from the existing `["fresh", "moderate", "high"]`
  vocabulary already used by the Cognitive Load persona (`fatigue: moderate`)
  and by the pre-existing `fatigue_degraded_precision` barrier.
- **`preferred_modality`:** `visual`.

**Card copy** — `SUMMARY_COPY.fatigue.high` already existed, unedited, since
the original build and reads *"A simpler interaction helps when energy is
low."*, close in spirit to the requested wording; `preferred_modality:
visual` supplies the second bullet. As with Profiles 4 and 5, this codebase's
`summarizeProfile()` renders one bullet per non-baseline dimension, so the
requested *"Repeated interactions can become tiring"* sentiment appears
instead as the barrier's own evidence text (below) — a fact about *this
environment's* flow length, not a general profile trait.

## Key finding before writing any code

The existing `fatigue_degraded_precision` barrier was checked first and
found **not** reusable for this profile's requirement — it is specifically
about temporarily reduced *precision* on small controls
(`min(width, height) < COMFORTABLE_TARGET_PX * 1.1`), not about the number of
interaction steps or repeated taps a flow requires. Forcing this profile's
"interaction burden" concept onto it would have been exactly the kind of
semantic mismatch the request warned against. A new, distinct barrier was
required — it and `fatigue_degraded_precision` legitimately co-fire for this
profile (same relationship the Cognitive Load persona already has to
multiple simultaneous barriers), each addressing a genuinely different
mismatch.

The standalone engine's `rules.py` already had a comment (from Phase 4)
explaining why a `fatigue_related_load` rule was deliberately **not**
implemented there — it would need a *live, session-derived* fatigue signal
this session-independent engine has no access to, and against only the
static baseline profile it would just restate the dexterity/cognition rules
under a different name. The new rule below is a different concept: it checks
a fact neither of those rules looks at (how many discrete interaction steps
the flow requires) against the same static baseline fatigue level — a
genuine, separate mismatch, not the same one under a new name. The original
comment was left in place and updated to note the distinction rather than
removed, so a future reader doesn't mistake this for a contradiction of that
earlier decision.

## New barrier: `excessive_interaction_burden`

Added to `Barrier.TYPE_CHOICES` (`backend/barriers/models.py`), implemented
in both existing engines (live `detection.py`, standalone `rules.py`) — the
same "two engines, one barrier type" pattern every prior profile phase
established.

**Trigger:** `fatigue` level is `moderate` or `high` (not `fresh`), **and**
the environment's interaction flow requires more than `COMFORTABLE_INTERACTION_STEPS`
(3) discrete steps/screens. Since the live engine's task parameter is
deliberately minimal (`{"task_id": ...}` only — confirmed by inspection that
`detect_barriers()` never actually reads its `task_descriptor` argument for
any existing rule), "how many steps does this flow require" is modeled as a
new **environment** fact, `interaction_step_count`, added to both fixtures —
the same category of fact `visible_choice_count` already is (a property that
is really about the task, encoded on the environment because that's what
both engines can see). The standalone engine, which does receive a real
`TaskDescriptor`, uses the environment fact when present and otherwise falls
back to the task's own real step count (`len(task.get("steps"))`) — the same
fallback shape `TooManyChoicesRule` already uses for `visible_choice_count`.

Severity: scales with fatigue severity and how far over the comfortable step
count the flow is (mirroring the `too_many_choices` formula shape in each
engine's own idiom).

**Live evidence example** (verified against a real session):
```
This kiosk flow currently requires 4 interaction steps (comfortable limit 3)
for a 'high' fatigue/stamina profile; repeated navigation and re-selection
add up over the course of the task. Includes repeated-tap controls: -, +.
```

This is a genuine `PROFILE + ENVIRONMENT → MISMATCH` check, not
`if profile == fatigue_reduced_stamina`: verified directly (both automated
tests and a live shell check) that (a) a `fresh`-fatigue profile against the
same 4-step environment produces no `excessive_interaction_burden` barrier,
and (b) a `high`-fatigue profile against an environment with
`interaction_step_count` at or below the comfortable threshold also produces
none — while `fatigue_degraded_precision` (a different, unrelated check)
correctly still fires in that second case, proving the two rules are
independent, not aliases of each other.

## Environment metadata added (both fixtures, additive only)

No existing control's id/width/height/label/x/y was touched — only new,
additive facts:
- A new top-level `"interaction_step_count": 4` fact on both
  `backend/fixtures/kiosk_standard.json` and
  `backend/environments/fixtures/ticket_kiosk_default.json`, reflecting the
  real 4-screen flow (`select_destination` → `select_ticket_type` →
  `select_quantity` → `confirm_purchase`) the `purchase_ticket` task already
  has.
- `"repeated_action": true` added to the `quantity_minus`/`quantity_plus`
  controls in `kiosk_standard.json` — exactly the suggested illustration of
  "a good demonstration of repetitive interaction burden": a real,
  descriptive fact used in the barrier's evidence text, not the numeric
  trigger itself (the trigger is `interaction_step_count`). The standalone
  fixture has no quantity controls to annotate this way and was left as-is
  rather than inventing new controls just for metadata.

## Logical steps vs. interaction burden

The four logical task selections — destination, ticket type, quantity,
confirm — are **unchanged**. `purchase_ticket`'s `TASK_STEPS` still has all
four required steps; the kiosk's `canBuy` gate still requires a destination
and a ticket type; quantity still defaults to 1 and is still adjustable.
Nothing about the business logic was removed or shortened, and no "fewer
task steps" claim is made anywhere in the UI or documentation. What changes
is **navigation**: the adapted kiosk puts ticket type and quantity on one
screen instead of two, removing one forced "Next" tap and one screen
transition. **AbilityOS reduces interaction burden without removing
required task requirements.**

## New adaptation: `streamline_task_flow`

Two existing adaptations were checked first, per the request, before adding
a new one:
- `simplify_navigation` (`flow: "simplified"`) and `step_by_step_flow`
  (`flow: "guided"`) are both real, legitimate candidates for
  `excessive_interaction_burden` — a simplified or fully guided flow does
  reduce burden somewhat — but neither is purpose-built for combining
  screens, and both carry a higher `interaction_cost`/`risk` than a
  purpose-built option needs to. Rather than force-selecting either one,
  both had `excessive_interaction_burden` added to their
  `resolves_barrier_types`, making them legitimate lower-scored secondary
  candidates the existing scoring engine can compare against the primary
  adaptation below — verified live: `streamline_task_flow` scores 2.50 vs.
  `step_by_step_flow`'s 2.39 and `simplify_navigation`'s 2.16 for the same
  barrier, an engine-driven outcome, not hardcoded.

Added to the **one shared** `Adaptation` catalogue (16 entries now):
```python
dict(
    name="streamline_task_flow",
    display_name="Streamline task flow",
    resolves_barrier_types=["excessive_interaction_burden"],
    modality="visual",
    accessibility_benefit=0.85, interaction_cost=0.20, risk=0.10,
    risk_level=Adaptation.RISK_LOW,
    ui_effects={"flow": "streamlined", "progress_indicator": True},
)
```

## Safety

**Zero new allowlist entries required** — unlike every prior profile phase,
`"flow"` and `"progress_indicator"` were already in `ALLOWED_UI_EFFECT_KEYS`
(`backend/adaptations/services/config.py`) from the pre-existing
`step_by_step_flow`/`simplify_navigation` adaptations; `"streamlined"` is
just a new *value* for an already-allowed key, not a new key. Both safety
validators remain fully generic/data-driven. Verified live: the candidate is
scored, approved by the rule engine, and never bypasses validation.

## Adaptive kiosk

`KioskView.jsx` gains a `streamlined` flow variant, distinct from the
pre-existing `guided` flow: when `appliedEffects.flow === "streamlined"`,
the kiosk's step list drops from 4 screens to 3 by rendering the "Ticket
Type" and "Quantity" sections together on the same step (selecting a ticket
type no longer auto-advances away from that screen), while destination and
confirm remain their own screens. This is a real reduction in navigation
transitions and forced taps, verified live via before/after screenshots —
not a claim of "fewer steps" in the business-logic sense, since all four
selections are still made and still required before BUY TICKET is enabled.

## Event tracking, task completion, feedback, learning signal

No changes needed anywhere in these layers — the existing `control_selected`
event already captures ticket-type and quantity picks regardless of which
screen they're shown on; `InteractionSession`, `Feedback`, and
`analytics.services.generate_learning_signal()` are all already fully
generic over `(adaptation_id, barrier_type, task_id)`. No fake "steps saved"
or "time saved" metric was invented anywhere — the only claims made are the
real, structural ones above (screen count, navigation taps).

## A real bug found and fixed during this phase

Live verification against the pre-existing Cognitive Load persona (which
already has `fatigue: moderate`) surfaced a genuine pre-existing edge case:
`excessive_interaction_burden` legitimately co-fires for that persona too
(same environment, same fatigue dimension, same threshold), so its session
now applies **two** adaptations that both set the `ui_effects.flow` key to
different values — `step_by_step_flow`'s `"guided"` and
`streamline_task_flow`'s `"streamlined"`. `InteractionOrchestrator.apply()`
(`backend/api/services/orchestrator.py`) merged applied adaptations' effects
by plain dict `.update()` in database-score order, so whichever adaptation
happened to sort last silently overwrote the other's conflicting key — in
the first live run this produced a session where the Developer Panel's
glance strip said *"Step-by-step guided flow"* while the kiosk actually
rendered the unrelated *streamlined* 3-step layout. Nothing crashed and the
purchase still completed correctly either way, but the rendered interface
didn't match the stated adaptation. This was never triggered by any
pre-existing profile, because no two of their simultaneously-applied
adaptations ever shared a `ui_effects` key before this phase.

Fixed by merging in ascending barrier-severity order, so the
*highest-severity* barrier's adaptation is applied last and wins any
conflicting key — the same "primary barrier" convention already used by
`barriers.sort(..., reverse=True)` and the Developer Panel's glance strip.
Verified live: Cognitive Load's merged `ui_effects.flow` is now `"guided"`
(matching its primary `too_many_choices` barrier), and the full 277-test
suite still passes. This is a no-op for every pre-existing profile, since
none of them ever had a key conflict to resolve.

## Testing

**16 new backend tests**, full suite **277/277 passing**:
- `barriers/tests.py` (live engine): triggers for `moderate`/`high` fatigue
  with a 4-step environment; **negative cases** — fresh fatigue against the
  same environment, and high fatigue against a comfortable (≤3-step)
  environment, both detect nothing; regression guard against the shared
  `STANDARD_KIOSK_ENV` fixture (no `interaction_step_count` fact at all).
- `barriers/test_rules.py` (standalone engine): the same coverage for
  `ExcessiveInteractionBurdenRule`, plus the task-step-count fallback and
  the `repeated_action` evidence field.
- `api/tests.py`: a full-stack test mirroring the five existing persona
  tests exactly, plus an explicit negative-case test confirming the Low
  Vision persona never sees `excessive_interaction_burden` even though the
  environment's flow length is the same for every profile.

**Live verification** (Playwright): the complete journey for Fatigue /
Reduced Stamina — including walking the adapted kiosk to confirm the
streamlined flow actually shows 3 step screens instead of 4 — plus a
regression pass re-running Cognitive Load, Speech Difficulty, and Low
Vision. Zero browser console errors across all four.

## Regression confirmation

All five existing profiles verified still fully functional via the full
automated suite (277/277); Cognitive Load, Speech Difficulty, and Low Vision
also re-run live end-to-end this phase. No existing barrier, adaptation, or
fixture field was modified — only additive facts and a new rule/adaptation.

## Demo steps

1. `python manage.py seed_demo` (idempotent).
2. Explore AbilityOS → select **Fatigue / Reduced Stamina** → Consent → Save
   Profile → Continue to Task & Environment.
3. Analyze Task → Analyze Environment → Detect Barriers (shows *"Excessive
   interaction burden"*) → Recommend Adaptation (shows *"Streamline task
   flow"*) → Open Adaptive Kiosk.
4. Start Ticket Purchase — note the 4-step progress header. Apply Approved
   Adaptation(s) — the header now reads "Step 1 of 3" / "Step 2 of 3" as
   Ticket Type and Quantity appear together on one screen.
5. Complete the purchase, submit feedback, and check the Developer Panel's
   glance strip and the Analytics dashboard.
