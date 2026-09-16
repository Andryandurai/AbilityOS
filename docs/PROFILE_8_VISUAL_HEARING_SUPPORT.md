# Profile 8 — Visual + Hearing Support

> **Naming note:** same convention as `docs/PROFILE_7_SLOWER_REACTION_SPEED.md`
> — this is "Phase 5" of the separate, new "add demo profiles 4–9"
> initiative, not this project's original Phases 1–8 (`docs/PHASES.md`).
> Named by profile, not by phase number, to avoid any collision.

## Objective

Add an eighth working demo profile — **Visual + Hearing Support** — fully
integrated through the existing pipeline, reusing the same `purchase_ticket`
task and `kiosk_standard` environment every other profile uses. No new
architecture, no duplicated engines, no profile 9.

## Product principle

"Visual + Hearing Support" represents a person who benefits from **both**
clearer visual presentation and a visual alternative to audio-only
information — a **functional** accessibility profile, never a diagnosis.
Audio is never removed; the requirement is that critical information must
not depend on sound *alone*.

## Key finding before writing any code

This is the first profile phase that required **zero new barrier or
adaptation code**. Both `audio_only_alert` and `low_contrast` already exist
in both engines (from the original project's Phase 4), already have
non-trivial trigger conditions (`hearing` in `{partial, relies-on-visual}`
for the former; `vision` in `{low-contrast-sensitive, large-text-needed}`
for the latter, both compared against real environment facts), and
`kiosk_standard`'s existing fixture data (`audio_alert: true,
visual_alert_mirror: false, contrast: 0.52`) already represents exactly the
mismatch this profile needs to demonstrate. Both existing adaptations
(`caption_audio`, `increase_contrast`) already resolve these barriers and
are already used independently by the Hearing Difficulty and Low Vision
personas respectively. `KioskView.jsx`'s rendering (the `kiosk--low-contrast`
/`kiosk--high-contrast` class toggle and the post-purchase banner) is already
driven generically by `barriers`/`appliedEffects`, not by profile name — so
it required no changes either. The **only** change this phase needed was the
new demo profile itself.

## Profile

- **Label:** Visual + Hearing Support · **Username:** `demo_visual_hearing_support`
- **Dimensions:** `vision: low-contrast-sensitive` (confidence 0.8) **and**
  `hearing: relies-on-visual` (confidence 0.8), both `source: manual` — the
  same controlled vocabulary and confidence convention every other primary-
  trait profile in this sub-initiative uses (e.g. Phase 2's `speech: limited`
  at 0.8, Phase 3's `fatigue: high` at 0.8).
- **`preferred_modality`:** `visual`.

**Card copy** — no changes needed. `SUMMARY_COPY.vision["low-contrast-
sensitive"]` ("Higher contrast makes text easier to read."),
`SUMMARY_COPY.hearing["relies-on-visual"]` ("Visual feedback is preferred
over audio."), and the `visual` modality copy ("Visual interaction is
preferred.") together already produce exactly the requested three bullets in
spirit, unedited — the same "check first, reuse if it already fits" outcome
as Phases 2, 3, and 4.

## Distinction from Profile 2 (Hearing Difficulty)

Profile 2 uses `hearing: relies-on-visual` alone (`vision: typical`) —
its only mismatch is `audio_only_alert`. Profile 8 uses the **same** hearing
value **plus** a non-typical vision value, so it legitimately produces
**both** `audio_only_alert` and `low_contrast` for the same environment —
the distinction lives entirely in the combination of existing ability
dimensions, exactly as the request specified, not in any new code path.

## Barriers: `audio_only_alert` + `low_contrast` (both reused, not added)

No barrier code was touched. Verified live against `kiosk_standard`:
```
audio_only_alert   severity 0.80  "Task raises an audio-only alert with no
                                    visual/haptic mirror; hearing level is
                                    'relies-on-visual'."
low_contrast       severity 0.73  "Screen contrast ratio 0.52 is below the
                                    0.60 comfortable threshold for vision
                                    level 'low-contrast-sensitive'."
```
Both fire from the unmodified, pre-existing rule engine — a genuine
`PROFILE + ENVIRONMENT → MISMATCH` check on both counts, verified negative
in three ways: a visual-alert-mirrored environment suppresses only
`audio_only_alert` (contrast barrier still fires); an adequate-contrast
environment suppresses only `low_contrast` (audio barrier still fires); an
environment resolving both facts produces zero barriers for this profile;
and a typical-vision/typical-hearing profile against the unmodified
environment produces neither.

## Adaptations: `caption_audio` + `increase_contrast` (both reused, not added)

No adaptation code was touched. Verified live: the existing scoring/safety/
apply pipeline selects both, with zero `ui_effects` key overlap (`banner_
alert`/`haptics` vs. `contrast`/`text_scale`), so both apply cleanly
alongside each other — no merge-order concern like Phase 3/4 encountered,
since these two adaptations happen to use entirely disjoint effect keys.
```
applied: ['increase_contrast', 'caption_audio']
ui_effects: {'contrast': 'high', 'text_scale': 1.3, 'banner_alert': True, 'haptics': True}
```

## Safety

No allowlist or validator changes — every `ui_effects` key involved
(`contrast`, `text_scale`, `banner_alert`, `haptics`) was already approved
before this phase.

## Adaptive kiosk

`KioskView.jsx` needed no changes: `contrastUnresolved`/`kiosk--low-
contrast` and `audioUnmirrored`/the post-purchase banner are already driven
generically by `hasBarrier(barriers, ...)` and `appliedEffects`, not by
profile identity. For this profile the kiosk genuinely renders both the
high-contrast styling and the success banner (the visual equivalent of the
audio alert) once both adaptations are applied — a real combination of two
independent, pre-existing rendering paths, not a new one.

## Event tracking, feedback, learning signal, analytics

No changes needed anywhere in these layers — all are already fully generic
over `(adaptation_id, barrier_type, task_id)`, exactly as every prior
profile phase found.

## Testing

**8 new backend tests**, full suite **297/297 passing**:
- `barriers/tests.py` (live engine): the combined profile detects both
  barriers on the standard environment; a mirrored-alert environment
  suppresses only the audio barrier; an adequate-contrast environment
  suppresses only the contrast barrier; an environment resolving both
  produces zero barriers.
- `api/tests.py`: a full-stack test mirroring the seven existing persona
  tests exactly, confirming both barriers are detected and both adaptations
  applied together; an explicit negative-case test confirming a typical-
  vision/typical-hearing profile (Speech Difficulty) never sees either
  barrier.

**Live verification** (Playwright): the complete journey for Visual +
Hearing Support (both barriers shown, both adaptations applied, high-
contrast kiosk + banner both visible), plus a regression pass re-running
Hearing Difficulty and Low Vision to confirm both remain correctly
distinct from this new combined profile. Zero browser console errors.

## Regression confirmation

All seven existing profiles verified still fully functional via the full
automated suite (297/297); Hearing Difficulty and Low Vision also re-run
live end-to-end this phase, confirmed to still produce only their own
single barrier each (not the combined pair). No existing barrier,
adaptation, or fixture field was modified.

## Demo steps

1. `python manage.py seed_demo` (idempotent).
2. Explore AbilityOS → select **Visual + Hearing Support** → Consent → Save
   Profile → Continue to Task & Environment.
3. Analyze Task → Analyze Environment → Detect Barriers (shows both
   *"Audio-only alert"* and *"Low contrast / small text"*) → Recommend
   Adaptation (shows both *"Caption / mirror audio alerts"* and *"Increase
   contrast"*) → Open Adaptive Kiosk.
4. Start Ticket Purchase — note the standard, lower-contrast presentation.
   Apply Approved Adaptation(s) — contrast visibly increases; completing the
   purchase now shows a visual success banner alongside the audio tone
   instead of audio alone.
5. Complete the purchase, submit feedback, and check the Developer Panel's
   glance strip and the Analytics dashboard.

---

**Profile 8 implemented end-to-end. Profile 9 remains untouched.**
