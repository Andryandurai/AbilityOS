# Demo Guide

## Setup (before judges arrive)

```bash
cd backend && python manage.py seed_demo && python manage.py runserver 4343
cd frontend && npm run dev
```

Open the frontend URL and click **Explore AbilityOS**.

## Quick demo — 3 minutes

1. **Select a demo user** — "Low Vision + Reduced Dexterity" (one of three real
   functional Ability Profiles, not fictional diagnoses).
2. **Consent** — pre-checked for this demo persona; click **Continue**.
3. **Ability Profile** — already filled in (`vision: large-text-needed`,
   `dexterity: reduced-precision`); click **Save Profile**.
4. **Profile Summary** — plain-language "AbilityOS Understands" statements;
   click **Continue to Task & Environment**.
5. **Analyze Task**, then **Analyze Environment** — the real Task/Environment
   Understanding engines return facts, not a barrier judgement yet.
6. **Detect Barriers** — shows `Small Tap Targets` and `Low Contrast / Small
   Text`, each with the exact measurement that triggered it.
7. **Recommend Adaptation** — shows the scored candidates, which one the
   AI/deterministic engine picked (`Increase Target Size`), and that the safety
   rule engine independently approved it.
8. **Open Adaptive Kiosk** — hands off into the real kiosk. Click **Start Ticket
   Purchase** (re-runs the same pipeline against the live session) then **Apply
   Approved Adaptation(s)**.
9. **Show standard vs. adaptive** — toggle **View Original** / **View Adaptive**
   on the kiosk card: identical component, same barriers, only the applied
   effects differ.
10. **Complete the task** — pick a destination, a ticket type, and **BUY
    TICKET**.
11. **Submit feedback** — the three-question screen (ease, did the adaptation
    help, did you need a person's help) plus an optional comment.
12. **Show the outcome** — the plain-language "Task complete ✓" summary, then
    the Developer Panel's `Outcome` section (completion time, assistance,
    feedback, a deterministic outcome score, and a structured learning signal).
13. **Open Analytics** in the header — standard-vs-adaptive comparison bars,
    per-adaptation observed outcomes, recent sessions.

## What to say

> "AbilityOS doesn't ask the person to adapt to the interface. It detects the
> mismatch between what this person can comfortably do, the task, and the
> environment — then changes the interaction, not the task."

When the barrier appears: *"This isn't a guess — the kiosk's real button is
120×40 pixels, and the comfortable target size for this dexterity level is 88
pixels. That's a measured mismatch, not an assumption."*

When the adaptation applies: *"The AI didn't invent this — it picked from a
fixed, pre-approved catalogue, and an independent rule engine checked it before
it was ever allowed to touch the interface."*

When feedback is submitted: *"AbilityOS doesn't just claim the adaptation
worked because the UI changed — it asks, and it measures completion, errors,
and whether a person needed help."*

Avoid overclaiming: say "adapts the interface" / "supports independent
interaction" / "generates an observed learning signal from this session" —
never "proves," "cures," "diagnoses," or "guarantees independence."

## Judge summary (at a glance)

| | |
|---|---|
| **WHO** | Reduced Dexterity |
| **WHAT** | Purchase Ticket |
| **WHERE** | Ticket Kiosk |
| **WHY** | Small Tap Targets (120×40px control vs. an 88px comfortable threshold) |
| **CHANGE** | Increase Target Size (approved by an independent safety rule engine) |
| **RESULT** | Task completed independently, no assistance requested |

This same table applies to the other two personas with a different barrier and
adaptation — see below.

## Second scenario — prove it's one engine, not one feature

Reset Demo → select **Cognitive Load** (pre-filled `cognition:
needs-step-by-step`, `fatigue: moderate`) → repeat steps 5–13. **Detected
barrier:** `too_many_choices` (8 visible choices vs. a 4-choice comfortable
limit). **Different adaptation wins:** `Step-by-step guided flow` — the kiosk
restructures into "Step 1 of 4" with a visible progress indicator, a genuinely
different rendering path driven by the same `KioskView` component reading
different `ui_effects`, not a hardcoded per-profile branch.

## Third scenario — Hearing Difficulty

Reset Demo → select **Hearing Difficulty**. **Detected barrier:**
`audio_only_alert` (the kiosk's purchase confirmation plays a tone with no
visual mirror by default). **Adaptation:** `Caption / mirror audio alerts` —
adds an on-screen banner and a vibration alongside the tone.

## Demonstrating assistance and abandonment

- On the kiosk, click **Ask staff for help** — it records the request and lets
  the person keep going (the button becomes "Help requested ✓" and disables,
  so one click can't be double-counted). Complete the task normally afterward;
  the Developer Panel's `Assistance` line will show the request.
- In a guided (step-by-step) flow, use the **← Back** control, then **Leave
  without finishing** to show an abandoned session — the outcome summary
  correctly reads "Task not completed" and the session is never counted as
  completed in Analytics.

## Optional: baseline comparison

Check "Run in baseline mode" before clicking Start — barriers are still
detected, but nothing is applied, so you can attempt the task on the
*unadapted* kiosk and watch the miss/shake feedback on undersized buttons.
That session's outcome feeds the "Standard" side of the Analytics comparison
for real.

## Optional: prove the profile editing is real, not decorative

From Profile Summary, click **Edit Profile**, change an answer, **Save**, and
show the Developer View now reflects the new value with `source: manual`.
**Clear Profile** resets every dimension to its default via a real API call.

## If something goes wrong

- **Blank profile list / "Could not reach the AbilityOS backend"** — the
  Django server isn't running, or `VITE_API_BASE_URL` (see
  `frontend/.env.example`) doesn't match its actual port.
- **No barriers detected** — run `python manage.py seed_demo` first; it seeds
  the environment fixtures the barrier detector reads from.
- **"Consent required" error** — the Consent step was skipped or revoked; go
  back through Select User → Consent.
- **A component crashed / blank screen** — the app-level error boundary should
  show "Something went wrong" with a **Return to AbilityOS** button; if you see
  a truly blank page, check the browser console and file it as a bug, not a
  demo gap.
- **Reset Demo** (header button) clears the current journey and reloads the
  demo-user selector — safe to use between judge groups without restarting
  either server; it never touches real (non-demo) data.
