# Demo Guide

A 3–5 minute walkthrough for judges, matching the spec's Part 15/17 demo flow.

## Setup (before judges arrive)

```bash
cd backend && python manage.py seed_demo && python manage.py runserver 4343
cd frontend && npm run dev
```

Open the frontend URL. You should see three Ability Profile cards: **Low Vision +
Reduced Dexterity**, **Hearing Difficulty**, **Cognitive Load**.

## Primary scenario — Low Vision + Reduced Dexterity

1. **Select the profile.** Click the "Low Vision + Reduced Dexterity" card.
2. **Consent gate.** Explain: AbilityOS never uses a profile without explicit,
   visible consent — click **I Agree**.
3. **Show the normal kiosk.** The kiosk preview appears greyed out (not yet
   interactive) — this is the standard, un-adapted "City Transit" ticket kiosk:
   small buttons, moderate contrast, several choices on one screen.
4. **Click "Start Ticket Purchase."** This runs the real pipeline: start session →
   analyze environment → detect barriers → recommend adaptations. Point out the
   **Developer / Explanation Panel** on the right:
   - *Ability Profile in use*: `vision: large-text-needed`, `dexterity: reduced-precision`.
   - *Detected barriers*: `small_tap_targets` (evidence: control is 120×40px vs. the
     88px comfortable threshold) and `low_contrast` (0.52 vs. 0.60 threshold).
   - *AI reasoning*: shows "Deterministic fallback" (no API key configured) or "AI
     decision engine" if you've set one — either way, expand "Show N candidates
     considered" to reveal the full scored list (`increase_target_size` beating
     `alternative_voice_input` despite lower raw benefit, because of cost/risk).
5. **Click "Apply Approved Adaptation(s)."** The kiosk visually transforms live:
   buttons enlarge, contrast flips to high-contrast white-on-black. This is a real
   CSS re-render driven by the approved adaptations' `ui_effects`, not a canned
   screenshot swap.
6. **Complete the purchase** in the now-adapted kiosk: pick a destination, a ticket
   type, and click **BUY TICKET**. "Ticket purchased" appears.
7. **Point at the Before/After panel** at the bottom — it just updated with this
   real session's numbers (completion rate, avg. time, avg. errors, assistance
   rate), aggregated live from the database.

## Second scenario — prove it's one engine, not one feature

8. **Switch to "Cognitive Load."** Click that profile card, agree to consent again,
   click **Start Ticket Purchase**.
9. **Detected barrier this time:** `too_many_choices` (8 visible choices vs. the
   4-choice comfortable limit). **Different adaptation wins:**
   `step_by_step_flow` — because a step-by-step wizard has the highest score for
   *this* barrier, not because it's hardcoded per profile.
10. **Apply it.** The kiosk restructures into "Step 1 of 4: Where are you going?"
    with a visible progress indicator — a genuinely different rendering path, driven
    by the same `KioskView` component reading different `ui_effects`.

## Optional: Hearing Difficulty

Switch to "Hearing Difficulty," run the task — the detected barrier is
`audio_only_alert` (the kiosk's buy confirmation plays a tone with no visual
mirror by default), and the winning adaptation is `caption_audio`, which adds an
on-screen banner + vibration alongside the tone.

## Optional: baseline comparison

Check "Run in baseline mode" before clicking Start — barriers are still detected and
shown in the developer panel, but nothing is applied, so you can attempt the task on
the *unadapted* kiosk and watch the miss/shake feedback on undersized buttons. That
session's outcome feeds the "Without AbilityOS" column of the metrics panel for
real, not as a hardcoded comparison number.

## If something goes wrong

- **Blank profile list / "Could not reach the AbilityOS backend"**: the Django
  server isn't running or `VITE_API_BASE_URL` doesn't match its port.
- **No barriers detected**: make sure `python manage.py seed_demo` was run — it
  seeds the `kiosk_standard` environment fixture the barrier detector reads from.
- **Reset Demo button**: clears all local UI state and reloads the profile list —
  use it between judge groups without restarting either server.
