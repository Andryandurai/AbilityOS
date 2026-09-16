# Profile 5 — Speech Difficulty

> **Naming note:** same convention as `docs/PROFILE_4_LIMITED_MOBILITY_REACH.md`
> — this is "Phase 2" of a separate, new "add demo profiles 4–9" initiative,
> not this project's original Phases 1–8 (`docs/PHASES.md`). Named by
> profile, not by phase number, to avoid any collision.

## Objective

Add a fifth working demo profile — **Speech Difficulty** — fully integrated
through the existing pipeline, reusing the same `purchase_ticket` task and
`kiosk_standard` environment every other profile uses. No new architecture,
no duplicated engines, no profiles 6–9.

## Product principle

"Speech Difficulty" is a **functional interaction requirement**, not a
medical diagnosis: *"speech-based interaction may be difficult or
unreliable."* The system prefers touch/text/visual confirmation over
requiring speech. No diagnostic or medical language appears anywhere in the
implementation.

## Profile

- **Label:** Speech Difficulty · **Username:** `demo_speech_difficulty`
- **Primary dimension:** `speech: limited` (confidence 0.8, `source: manual`)
  — reused directly from `abilities/constants.py`'s existing
  `["typical", "limited", "unavailable"]` vocabulary (present since Phase 2
  of the original project, unused by any profile until now).
- **`preferred_modality`:** `visual`.

**Card copy** — `SUMMARY_COPY.speech.limited` already existed, unedited,
since the original Phase 2 build and reads almost verbatim as requested
("Non-voice input methods work best."); `preferred_modality: visual`
supplies the third bullet ("Visual interaction is preferred."). As with
Profile 4, the middle requested bullet ("Speech-based interaction may be
difficult or unreliable") isn't a separate card bullet — this codebase's
`summarizeProfile()` renders one bullet per non-baseline dimension, and that
exact sentiment appears instead as the barrier's own evidence text (below),
which is arguably its more correct home — it's a fact about *this
environment's* interaction requirement, not a general profile trait.

## Key finding before writing any code

The existing `alternative_voice_input` adaptation ("Lets the person
complete the task by speaking instead of touching the screen") is the
**opposite** of what this profile needs — it exists for dexterity-impaired
users who want voice *instead of* touch. It was not reused; a new,
oppositely-directed adaptation was required.

## New barrier: `voice_only_input`

Added to `Barrier.TYPE_CHOICES` (`backend/barriers/models.py`), implemented
in both existing engines (live `detection.py`, standalone `rules.py`) — the
same "two engines, one barrier type" pattern Profile 4 established.

**Trigger:** `speech` level is `limited` or `unavailable` (not `typical`),
**and** the environment declares a control with `interaction_type: "voice"`.
Severity: `limited` → 0.6 (live) / 0.55 (standalone), `unavailable` → 0.85 /
0.8.

**Live evidence example** (verified against a real session):
```
The kiosk offers a voice-based interaction ('Speak your destination') for
this task; speech-based interaction is required or suggested, while a
'limited' speech profile prefers non-speech input.
```

This is a genuine `PROFILE + ENVIRONMENT → MISMATCH` check, not
`if profile == speech_difficulty`: verified directly (both automated tests
and a live shell check) that a `typical`-speech profile against the exact
same voice-offering environment produces **zero** barriers.

## Environment metadata added (both fixtures, additive only)

One new, non-primary control — exactly the shape suggested in the request —
added to both fixtures; no existing control's id/width/height/label/x/y was
touched:
```json
{ "id": "voice_destination", "type": "voice_prompt", "label": "Speak your destination", "interaction_type": "voice" }
```
This represents a real environmental capability (the kiosk *can* offer a
voice prompt for destination selection), present regardless of profile —
the same relationship the pre-existing `audio_alert` fact has to the
`audio_only_alert` barrier. `visible_choice_count` was left unchanged in
both fixtures (it's a separate, manually-set fact, not derived from the
`controls` array length), so this addition does not affect the Cognitive
Load profile's `too_many_choices` barrier.

## New adaptation: `touch_text_alternative`

Added to the **one shared** `Adaptation` catalogue (14 entries now):
```python
dict(
    name="touch_text_alternative",
    display_name="Touch/text alternative",
    resolves_barrier_types=["voice_only_input"],
    modality="visual",
    accessibility_benefit=0.9, interaction_cost=0.15, risk=0.05,
    risk_level=Adaptation.RISK_LOW,
    ui_effects={"touch_text_mode": True},
)
```

**Visual confirmation as a secondary candidate** (request section 8): rather
than force-adding an unrelated adaptation, `voice_only_input` was added to
the *existing* `confirmation_before_irreversible_action`'s
`resolves_barrier_types` list — a real, additional candidate the existing
scoring engine now naturally considers and (correctly) scores lower than
the primary adaptation. Verified live: `touch_text_alternative` scores 2.52
vs. `confirmation_before_irreversible_action`'s 1.99 for the same barrier —
an engine-driven outcome, not hardcoded. This change has zero effect on
Profiles 1/4, whose barriers this adaptation already resolved unchanged.

## Safety

Only change required: added `"touch_text_mode"` to the existing
`ALLOWED_UI_EFFECT_KEYS` allowlist (`adaptations/services/config.py`) — both
safety validators are fully generic/data-driven and needed no bespoke rule.
Verified live: approved by the rule engine, never bypasses validation.

## Adaptive kiosk

`KioskView.jsx` reads the new `touch_text_mode` key. Before the adaptation
is applied, a real voice-prompt note ("🎤 This kiosk suggests speaking your
destination.") appears above the touch destination grid — touch still works
underneath (this profile is nudged, not blocked, matching how every other
unresolved barrier in this kiosk behaves). After applying, the heading
changes to *"Choose a destination:"* and a confirmation appears: *"✓ Touch
and text selection available — no speech required."* — a real rendering
change, verified live via before/after screenshots, not just a claim in
text.

## Event tracking, task completion, feedback, learning signal

No changes needed anywhere in these layers — the existing `control_selected`
event already captures a touch destination pick; `InteractionSession`,
`Feedback`, and `analytics.services.generate_learning_signal()` are all
already fully generic over `(adaptation_id, barrier_type, task_id)`. No new
event type was added (none was needed). Verified live: completing a
purchase with this profile applied produces
`applied_adaptations: ["touch_text_alternative"]` and the session correctly
feeds the Analytics dashboard.

## Testing

**13 new backend tests**, full suite **264/264 passing**:
- `barriers/tests.py` (live engine): triggers for `limited`/`unavailable`
  speech with a voice control present; **negative case** — a `typical`
  speech profile against the identical voice-offering environment detects
  nothing; regression guard against the shared `STANDARD_KIOSK_ENV` fixture.
- `barriers/test_rules.py` (standalone engine): same coverage for
  `VoiceOnlyInputRule`, including the negative case.
- `api/tests.py`: a full-stack test mirroring the four existing persona
  tests exactly, plus an explicit negative-case test confirming the Low
  Vision persona never sees `voice_only_input` even though the environment
  always offers the voice control.

**Live verification** (Playwright): the complete journey for Speech
Difficulty, plus a regression pass re-running Low Vision, Hearing
Difficulty, and Limited Mobility + Reach. **Zero browser console errors**
across all four.

## A real bug found and fixed during this phase

Adding the fifth demo profile pushed the full test suite's request volume
against `/api/interactions/start/` over Phase 8's `session_start` rate
throttle (30/min) — not because of a real abuse pattern, but because DRF's
`ScopedRateThrottle` state lives in Django's default in-memory cache, which
(unlike the database) is **not** reset between `TestCase` classes, so it
accumulates across the entire `manage.py test` run. Fixed centrally in
`backend/config/settings.py`: a `TESTING = "test" in sys.argv` flag relaxes
the throttle rates only when running under the test runner; production
behavior is completely unchanged. A separate, unrelated, pre-existing
fragility was also found and fixed in `barriers/test_rules.py`'s
`RegressionTests` (a hardcoded `user_id=1` assumption, replaced with a
lookup by username) — real, but not the actual cause of the failure; several
other pre-existing tests share the same hardcoded-id pattern and were **not**
touched, since they aren't currently failing and fixing all of them would
be unrelated scope creep beyond this phase.

## Regression confirmation

All four existing profiles verified still fully functional (Low Vision,
Hearing Difficulty, and Limited Mobility + Reach re-run live end-to-end
this phase; Cognitive Load's backend logic untouched and covered by its own
existing passing tests). All 255 pre-existing backend tests still pass
unmodified.

## Demo steps

1. `python manage.py seed_demo` (idempotent).
2. Explore AbilityOS → select **Speech Difficulty** → Consent → Save Profile
   → Continue to Task & Environment.
3. Analyze Task → Analyze Environment → Detect Barriers (shows *"Voice-only
   / speech-dependent interaction"*) → Recommend Adaptation (shows
   *"Touch/text alternative"*) → Open Adaptive Kiosk.
4. Start Ticket Purchase — note the voice-prompt note above the destination
   grid. Apply Approved Adaptation(s) — the note is replaced by *"Choose a
   destination:"* and a *"no speech required"* confirmation.
5. Complete the purchase using only touch, submit feedback, check the
   Developer Panel's glance strip and the Analytics dashboard.
