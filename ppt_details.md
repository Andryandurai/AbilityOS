# AbilityOS — Hackathon Presentation Content & Canva Design Guide

> **How to use this file:** This is not developer documentation. It is a
> ready-to-copy content pack for building the AbilityOS pitch deck in
> Canva. Every technical claim below (technology names, barrier names,
> adaptation names, API paths, persona count) was verified directly
> against the current repository — nothing here is invented or aspirational
> unless explicitly labeled "Future Scope."
>
> Track: BME × Assistive Technology · Challenge theme: **One Small Change**

---

## HOW THIS DECK IS ORGANIZED

14 slides, one coherent story:

1. Title → 2. Problem → 3. Why current systems fail → 4. Our solution →
5. How it works → 6. Reasoning engine → 7. Tech stack → 8. Architecture →
9. Live demo/use case → 10. 9 ability profiles → 11. Before/after →
12. Impact → 13. Future scope → 14. Conclusion

The single idea to protect on every slide:

```
FIXED DIGITAL SYSTEM
        ↓
PERSON + TASK + ENVIRONMENT
        ↓
FUNCTIONAL BARRIER
        ↓
SMALLEST USEFUL ADAPTATION
        ↓
ADAPTIVE INTERACTION
        ↓
INDEPENDENT OUTCOME
```

**Never let a judge think "this is a ticket-booking app."** The kiosk is
the demonstration vehicle. AbilityOS — the reasoning layer — is the product.

---

# SLIDE 1 — TITLE

## Slide Objective
Open with identity and positioning in under 5 seconds of reading time — this is a reasoning platform, not a medical tool and not a kiosk app.

## Main Heading
ABILITYOS

## Subheading
An Operating System for Human Abilities

## Slide Content
- Tagline: **"Technology that adapts to the person — not the other way around."**
- One-liner: *"An adaptive accessibility reasoning layer that turns functional barriers into safe, personalized interactions."*
- Small footer tag: Track 04 — BME × Assistive Technology · "One Small Change"

## Key Message
AbilityOS adapts the interface to the person, not the person to the interface.

## Visual Suggestion
A single stylized human silhouette at the center, with a soft interface panel around them that visibly reshapes (larger controls on one side, a caption bubble on another, extra spacing on another) — the system bending around the person, not the other way around.

## Canva Layout
Full-bleed light background. Centered title block (logo-style "AbilityOS" wordmark + subheading directly beneath). Tagline in italics, smaller, centered below. One-liner in a light card near the bottom third. Track/challenge tag in a small pill, bottom-left corner.

## Speaker Notes
"AbilityOS is not another accessibility toggle, and it's not a ticket-booking app — you'll see a kiosk in a moment, but that's just our demonstration environment. What we've built is a reasoning layer that understands a person's functional abilities, watches the task and environment, and adapts the interaction — safely and automatically."

## Design Notes
Title font: modern bold sans-serif (e.g., Poppins/Sora/Manrope Bold), large, high contrast against background. Body font: clean readable sans-serif (e.g., Inter/Work Sans). No medical iconography (no crosses, no stethoscopes, no hospital imagery). Deep blue/teal accent only — keep 80%+ of the slide white/light space.

---

# SLIDE 2 — THE PROBLEM

## Slide Objective
Establish that accessibility problems are functional mismatches, not medical conditions — and that they're common, not rare.

## Main Heading
The Same Interface Doesn't Work Equally Well for Everyone

## Subheading
Digital systems assume one "average" user — real people don't match that average.

## Slide Content
- Small touch targets → difficult for reduced-precision touch
- Low-contrast information → hard to perceive
- Audio-only alerts → exclude anyone who relies on visual information
- Too many choices at once → increases cognitive interaction burden
- Short response windows → disadvantage slower reactions
- Distant controls → create physical reach barriers
- Speech-dependent interaction → a barrier for speech difficulty
- Repeated interactions → become tiring over a task
- Crowded controls → increase accidental activation

## Key Message
These are functional mismatches between a person and an environment — not medical diagnoses.

## Visual Suggestion
A simple equation graphic: a person icon + a screen/kiosk icon → an "=" → a warning/mismatch icon, with the word "BARRIER" beneath it. Surround with small icon chips for each bullet (tap target, speaker, eye, clock, hand-reach, mic, battery, cursor-cluster).

## Canva Layout
Left third: the PERSON + SYSTEM = MISMATCH → BARRIER equation, vertically stacked. Right two-thirds: a 3×3 or 3×3-ish grid of small icon+one-line cards, one per bullet. Keep each card to a single short line.

## Speaker Notes
"None of these are about what's medically 'wrong' with someone. They're about a mismatch: this person's functional ability, this task, this specific environment. The same person might face zero barriers in one context and a real barrier in another — that's the insight the whole system is built on."

## Design Notes
Use consistent thin-line icons (one style family) for all 9 bullet chips. Warning/mismatch icon in the amber/orange accent only — don't overuse red (keeps tone constructive, not alarming).

---

# SLIDE 3 — WHY CURRENT SYSTEMS FAIL

## Slide Objective
Show the structural gap between "accessibility as a static setting" and "accessibility as live reasoning."

## Main Heading
Static Accessibility Settings Don't Reason About the Moment

## Subheading
Traditional systems apply one fixed interface to everyone, or a manual toggle a person has to find and set themselves.

## Slide Content
Traditional approach:
```
User → Fixed Interface
```
AbilityOS approach:
```
User + Task + Environment
   → Detect Barrier
   → Select Adaptation
   → Validate Safety
   → Adaptive Interface
```

Comparison table:

| Traditional Systems | AbilityOS |
|---|---|
| Static interface | Context-aware adaptation |
| One-size-fits-all | Person-specific |
| Manual settings | Functional reasoning |
| Feature-based | Barrier-based |
| Accessibility as a mode | Accessibility as an interaction layer |

## Key Message
AbilityOS reasons about the specific person, task, and environment in front of it — every time, not once at setup.

## Visual Suggestion
A simple two-row flow diagram (traditional vs. AbilityOS) stacked vertically, followed by the 5-row comparison table below it.

## Canva Layout
Top half: two short horizontal flow diagrams, labeled "Traditional" and "AbilityOS," using arrow-connected boxes. Bottom half: the 5-row comparison table, alternating row shading, teal accent on the AbilityOS column header.

## Speaker Notes
"Most accessibility features today are switches someone has to know exist and turn on themselves — a fixed larger-text mode, a fixed high-contrast mode. AbilityOS instead reasons live: it looks at who's using the system, what they're trying to do, and what this specific screen currently demands — then decides if there's a real mismatch worth fixing."

## Design Notes
Keep the table minimal — no more than 5 rows, generous row height, one accent color reserved for the "AbilityOS" column only so the contrast is visually obvious at a glance.

---

# SLIDE 4 — OUR SOLUTION: ABILITYOS

## Slide Objective
Introduce AbilityOS as the product, and clearly separate it from its demonstration environment.

## Main Heading
Meet AbilityOS

## Subheading
An adaptive accessibility reasoning layer — not a ticket kiosk app.

## Slide Content
- *"AbilityOS understands a person's functional abilities, the task they are performing, and the environment they are interacting with — then applies the smallest safe change needed to reduce the barrier."*
- Flow: `PERSON → TASK → ENVIRONMENT → BARRIER → ADAPTATION → OUTCOME`
- Callout: **"Adapt the technology — not the person."**
- Current Proof-of-Concept: **Adaptive Public Ticket-Purchase Kiosk**

## Key Message
The kiosk is one demonstration environment; AbilityOS itself is the reusable reasoning layer behind it.

## Visual Suggestion
A vertical 6-step flow diagram (Person → Task → Environment → Barrier → Adaptation → Outcome) as the visual centerpiece, with a small labeled tag off to the side reading "Current demo: Ticket Kiosk" pointing at the whole diagram — making clear the kiosk sits *outside* and *below* the reasoning layer.

## Canva Layout
Center-aligned vertical pipeline with 6 rounded rectangle nodes connected by downward arrows. Directly below the pipeline, a smaller, visually distinct card labeled "Current Proof-of-Concept: Adaptive Public Ticket-Purchase Kiosk" — deliberately smaller and lower to signal "this is just where we're showing it today."

## Speaker Notes
"This is the core loop: person, task, environment, barrier, adaptation, outcome. Today we're showing it through a ticket-purchase kiosk because it's a controlled, measurable environment — but this reasoning loop isn't about ticket kiosks. It's a layer that could sit behind any digital interaction."

## Design Notes
Use a distinctly different visual weight (lighter card, dashed border, smaller font) for the "Current Proof-of-Concept" callout versus the main pipeline, so it reads as secondary/illustrative rather than the main point.

---

# SLIDE 5 — HOW ABILITYOS WORKS

## Slide Objective
Walk the judge through the full reasoning pipeline stage by stage.

## Main Heading
The Complete Reasoning Workflow

## Subheading
Twelve stages, one continuous loop — no step skipped, no step decided by the frontend.

## Slide Content
```
USER
 ↓
ABILITY PROFILE      "Captures consented functional requirements."
 ↓
TASK                 "Understands what the user is trying to accomplish."
 ↓
ENVIRONMENT          "Describes the interaction demands."
 ↓
BARRIER DETECTION    "Identifies the mismatch."
 ↓
ADAPTATION SCORING   "Selects the smallest useful intervention."
 ↓
OPTIONAL AI RANKING  "May explain or re-rank approved candidates only."
 ↓
SAFETY VALIDATION    "Ensures only approved and safe changes are applied."
 ↓
ADAPTIVE INTERACTION "Changes the interface without changing the task itself."
 ↓
OUTCOME              "Measures whether the task was completed."
 ↓
FEEDBACK             "Asks the person whether the change actually helped."
 ↓
ANALYTICS / LEARNING SIGNAL  "Turns sessions into structured evidence."
```

## Key Message
Every stage is a real, separate step — nothing here is a shortcut from profile straight to UI change.

## Visual Suggestion
A tall vertical stepper/timeline down the center of the slide, 12 small nodes, each with its one-line description to the side (alternating left/right to keep it readable at this length).

## Canva Layout
Vertical timeline spine down the middle. Alternate description text left/right of each node to avoid a long single-column wall of text. Use a distinct icon per stage (profile card, checklist, map pin, magnifying glass, scale/balance, sparkle for AI, shield for safety, screen, checkmark, speech bubble, bar-chart).

## Speaker Notes
"Notice there's no shortcut from 'who the user is' straight to 'what the screen looks like.' Every one of these 12 stages runs for real, in this order, for every session — and two of them matter most for trust: Safety Validation, which is the one authority that can approve or reject a change, and Feedback, which is how we know whether the change actually helped instead of just assuming it did."

## Design Notes
Because this stage list is longer than most slides, keep each description to 4–6 words max on-slide; put the full sentence in speaker notes only.

---

# SLIDE 6 — ADAPTIVE REASONING ENGINE

## Slide Objective
Show the judge that decisions are computed, explainable, and safety-gated — not a hardcoded if/else on profile name.

## Main Heading
It Doesn't Just Turn Accessibility On or Off — It Reasons

## Subheading
Every decision is scored, explained, and validated before it ever reaches the screen.

## Slide Content
- The system explains itself along: **WHO → WHAT → WHERE → WHY → CHANGE → SAFETY → RESULT**
- Scoring formula:
```
Score =
  Accessibility Benefit
+ Task Relevance
+ User Preference
+ Confidence
− Interaction Cost
− Risk
```
- *"Candidate adaptations are generated from an approved catalogue and ranked by relevance, benefit, confidence, preference, cost, and risk."*
- Architecture principle: **"The LLM proposes; the rule engine disposes."**
- Deterministic rules detect barriers → approved catalogue constrains adaptations → AI is optional → safety validation stays authoritative → the frontend never makes the final accessibility decision.

## Key Message
AI can suggest and explain — it never gets to invent a barrier, invent an adaptation, or bypass safety.

## Visual Suggestion
The scoring formula as a clean equation card (plus/minus symbols large and clear), with a small "WHO → WHAT → WHERE → WHY → CHANGE → SAFETY → RESULT" strip above it, and the "LLM proposes; rule engine disposes" line as a standalone pull-quote below.

## Canva Layout
Top strip: 7 small labeled chips (WHO/WHAT/WHERE/WHY/CHANGE/SAFETY/RESULT) in a single row. Middle: the scoring formula as a large, centered equation card. Bottom: the "LLM proposes; rule engine disposes" pull-quote, set apart in a bordered box with a distinct accent color.

## Speaker Notes
"This is the slide that answers 'is this just a bunch of if-statements?' It isn't — every candidate adaptation is scored on this exact formula, benefit and relevance and confidence and preference, minus cost and risk. If an AI provider is configured, it can rank or explain the already-approved candidates — but it can never invent a new one, and it can never skip safety validation. That's the rule we designed the whole system around."

## Design Notes
Don't overfill this slide — it's meant to feel like the "credibility" slide. Generous whitespace around the formula card. Use one strong accent color for the pull-quote box so it's the visual anchor of the slide.

---

# SLIDE 7 — TECHNOLOGY STACK

## Slide Objective
Establish technical credibility using only technologies verified as actually present in the repository.

## Main Heading
Built on a Real, Working Stack

## Subheading
Every technology below is actually installed and running in this codebase — nothing here is aspirational.

## Slide Content

**Frontend**
- React 19 + Vite — the kiosk, developer panel, and analytics dashboard
- Plain JavaScript (JSDoc types) — no TypeScript build step
- `oxlint` — frontend linting

**Backend**
- Django 5.2 + Django REST Framework — the application server and REST API
- `djangorestframework-simplejwt` — JWT authentication infrastructure
- `django-cors-headers` — cross-origin requests from the React frontend

**Database**
- SQLite — zero-setup local/demo default
- PostgreSQL — production-ready path via `DATABASE_URL` (`psycopg2`, `dj-database-url`)

**AI Decision Engine (Optional)**
- Provider-agnostic LLM client — OpenAI/Anthropic-compatible
- Pydantic — validates every AI response before it's trusted
- Fully optional: the deterministic scoring formula runs the whole pipeline with no AI key configured

**Computer Vision (Optional, off by default)**
- OpenCV + Tesseract OCR — environment analysis path, implemented but disabled by default (`VISION_ENABLED=false`); the demo runs on structured JSON environment data

**Browser Interaction APIs**
- Web Speech Synthesis — on-demand text-to-speech
- Vibration API — haptic confirmation
- Web Audio API — audio alert tones

**Testing & Tooling**
- Django's built-in test runner — 310 automated backend tests
- Playwright — live frontend verification
- Git — version control

## Key Message
This is a real, running full-stack system — not a mockup, and not a stack list padded with unused technologies.

## Visual Suggestion
A clean 2×4 (or 4×2) card grid, one card per category, each with a small category icon and a short bullet list.

## Canva Layout
Grid of rounded cards, consistent icon size top-left of each card, category name bold, technologies as a tight bullet list beneath. Keep the "Optional" categories (AI, Computer Vision) visually marked with a small "optional" tag/badge so judges don't assume they're always active.

## Speaker Notes
"Everything on this slide is actually running in the repository — we were careful not to list a technology just because it's common in this space. The AI engine and the computer-vision path are both real and implemented, but both are optional by design: the deterministic path is what makes the demo work every time, with or without an API key."

## Design Notes
Use one consistent icon set (line icons) across all 8 cards. "Optional" badges should use a neutral gray, not a red/warning color — optional isn't a weakness here, it's a deliberate design choice.

---

# SLIDE 8 — SYSTEM ARCHITECTURE

## Slide Objective
Make the layered architecture understandable to a non-technical judge in one glance.

## Main Heading
System Architecture

## Subheading
One reasoning core, cleanly separated from the interface that renders it.

## Slide Content
```
USER
 ↓
REACT FRONTEND
 ↓
DJANGO REST API
 ↓
ABILITYOS CORE
 ├── Ability Profile
 ├── Task Understanding
 ├── Environment Understanding
 ├── Barrier Detection
 ├── Adaptation Engine
 ├── AI Decision Engine (Optional)
 └── Safety Validation
 ↓
ADAPTIVE KIOSK
 ↓
USER OUTCOME
 ↓
SESSION / EVENTS
 ↓
FEEDBACK
 ↓
ANALYTICS
 ↓
LEARNING SIGNAL
 ↓
DATABASE (SQLite / PostgreSQL)
```

Block meanings:
- **React Frontend** — renders only backend-approved effects; makes no accessibility decisions itself.
- **Django REST API** — the single entry point every request passes through.
- **AbilityOS Core** — 7 modules that together run the full Person→Barrier→Adaptation reasoning.
- **Adaptive Kiosk** — the demonstration surface the reasoning actually changes.
- **Session / Events / Feedback / Analytics / Learning Signal** — the outcome-measurement half of the loop.
- **Database** — every session, event, and piece of feedback persisted as real rows.

## Key Message
The reasoning core sits in one place, between the interface and the database — never inside the frontend.

## Visual Suggestion
A vertical layered diagram: 3 wide horizontal bands (Frontend / API / Core) stacked, with the Core band containing 7 smaller labeled sub-blocks in a 2-column mini-grid, then a continuing pipeline below (Kiosk → Outcome → Session → Feedback → Analytics → Learning Signal → Database).

## Canva Layout
Top: "USER" as a small icon. Below: 3 full-width bands, clearly bordered, labeled "REACT FRONTEND," "DJANGO REST API," "ABILITYOS CORE" — the Core band is taller and contains the 7 sub-module chips arranged 2×4 (one empty/decorative slot or a logo mark). Below the Core band, a single-column arrow chain for the remaining 7 stages, ending at a database icon.

## Speaker Notes
"This is deliberately layered: the React frontend only renders what the backend approves — it never calculates a barrier or a score itself. Everything that matters — detecting the barrier, scoring the adaptation, validating safety — happens inside the AbilityOS Core, one layer, seven modules, sitting cleanly between the interface and the database."

## Design Notes
Use a distinctly bordered/shaded "container" for the AbilityOS Core band so it visually reads as the "engine room" of the diagram — everything else should look like plumbing around it.

---

# SLIDE 9 — LIVE DEMONSTRATION / USE CASE

## Slide Objective
Justify the choice of demonstration environment and reframe it correctly before the demo begins.

## Main Heading
Proof-of-Concept: Adaptive Public Ticket-Purchase Kiosk

## Subheading
Chosen because it's measurable — not because AbilityOS is a ticketing product.

## Slide Content
- *"We chose ticket purchase as a controlled reference task because it contains measurable interaction demands — touch targets, visual information, choices, alerts, timing, and confirmation — allowing the complete AbilityOS reasoning pipeline to be demonstrated and measured."*
- Task: **`purchase_ticket`** (select destination → select ticket type → select quantity → confirm purchase)
- Environment: **`kiosk_standard`**
- Core proof:
```
SAME KIOSK + DIFFERENT PERSON = DIFFERENT BARRIER = DIFFERENT ADAPTATION
```

## Key Message
The kiosk is the demonstration vehicle; AbilityOS is the product being demonstrated.

## Visual Suggestion
A single kiosk illustration/screenshot in the center, with three arrows radiating outward to three small "person → barrier → adaptation" mini-cards, showing the same kiosk producing three different outcomes.

## Canva Layout
Center: kiosk screenshot/illustration. Three short connector lines to three compact cards around it, each reading "Person X → Barrier Y → Adaptation Z." Bottom banner: the "SAME KIOSK + DIFFERENT PERSON = ..." equation in large type.

## Speaker Notes
"Buying a ticket has everything we need to prove the concept: small buttons, an audio alert, several choices, a countdown, a confirmation step — one task, several kinds of real interaction demand. What you're about to see is the same kiosk, the same task, producing a different barrier and a different fix depending on who's using it."

## Design Notes
Avoid making this look like a ticketing-product ad — keep the kiosk illustration schematic/wireframe-styled rather than glossy/branded, to reinforce "this is a test environment," not a product.

---

# SLIDE 10 — 9 ABILITY PROFILES

## Slide Objective
Prove breadth: one engine, nine genuinely different functional profiles, each producing its own real barrier and adaptation.

## Main Heading
One Engine. Nine Functional Profiles.

## Subheading
Every barrier and adaptation below is real and verified against the live system — not illustrative.

## Slide Content
3×3 grid, one card per profile:

1. **Low Vision + Reduced Dexterity** — Barrier: Small tap targets · Low contrast → Adaptation: Increase target size + Increase contrast
2. **Hearing Difficulty** — Barrier: Audio-only alert → Adaptation: Caption / mirror audio alerts
3. **Cognitive Load** — Barrier: Too many choices → Adaptation: Step-by-step guided flow
4. **Limited Mobility + Reach** — Barrier: Controls outside comfortable reach → Adaptation: Reachable control layout
5. **Speech Difficulty** — Barrier: Voice-only / speech-dependent interaction → Adaptation: Touch/text alternative
6. **Fatigue / Reduced Stamina** — Barrier: Excessive interaction burden → Adaptation: Streamline task flow
7. **Slower Reaction Speed** — Barrier: Time-limited interaction → Adaptation: Increase interaction timeout
8. **Visual + Hearing Support** — Barrier: Audio-only alert + Low contrast → Adaptation: Caption / mirror audio alerts + Increase contrast
9. **High Interaction Sensitivity** — Barrier: Accidental activation risk → Adaptation: Increase spacing

## Key Message
Nine real functional profiles, nine real barriers, nine real adaptations — from the same task, the same environment, and the same reasoning engine.

## Visual Suggestion
A clean 3×3 card grid, each card: profile name (bold), a small barrier icon + label, an arrow, a small adaptation icon + label.

## Canva Layout
Equal-sized rounded cards in a strict 3×3 grid, consistent internal layout (name top, barrier/adaptation pair beneath separated by a small arrow icon). Use one accent color per card border cycling through a small palette so the grid feels varied but still unified.

## Speaker Notes
"This is the breadth slide. Nine different functional profiles — none of them medical labels — each hitting the same kiosk and task, and each one producing its own genuinely different barrier and its own genuinely different fix. Notice profile 8 combines two real barriers at once, because it combines two real functional needs — the engine doesn't need special-case code for that, it just runs the same reasoning twice."

## Design Notes
Keep every card the exact same text length by trimming barrier/adaptation labels to 2–4 words — put the full sentence-level description only in speaker notes, never on the card itself.

---

# SLIDE 11 — BEFORE VS AFTER

## Slide Objective
Make the transformation viscerally obvious with a direct side-by-side, while being honest that the specific change depends on the detected barrier.

## Main Heading
From Fixed Interface to Adaptive Interaction

## Subheading
Adaptations are selected according to the detected barrier — not every change happens for every user.

## Slide Content
**STANDARD**
- Small controls
- Lower visual clarity
- Audio-only alert
- Crowded choices
- Short response window
- Immediate consequential action

**ADAPTIVE**
- Larger / separated controls
- Higher contrast
- Visual / captioned alerts
- Simplified / guided flow
- Extended response time
- Explicit confirmation

- Framing line: **SAME TASK → DIFFERENT ADAPTATION**

## Key Message
The task never changes — only the interaction layer changes, and only for the barrier actually detected.

## Visual Suggestion
A vertical split-screen: left half labeled "STANDARD" in muted/gray tones showing a cramped kiosk mockup; right half labeled "ADAPTIVE" in the brand accent color showing the same kiosk with visibly larger spacing, a caption banner, and a confirmation dialog.

## Canva Layout
50/50 vertical split down the center. Left side deliberately duller/grayscale-leaning; right side in full color with the accent palette. A single bold divider line down the middle with "SAME TASK →" printed on it. Small disclaimer line beneath both halves: "Adaptations are selected according to the detected barrier."

## Speaker Notes
"This is deliberately not 'every feature turned on for everyone.' The left side is the standard kiosk. The right side shows the range of adaptations the system can apply — but for any single person, only the adaptations relevant to their actual detected barrier are applied. Same task on both sides — that's the point."

## Design Notes
Resist the temptation to show all 6 adaptive changes active simultaneously in one screenshot if using a real product screenshot — either use a composite/illustrative mockup, or caption it clearly as "illustrative range of adaptive changes."

---

# SLIDE 12 — IMPACT & BENEFITS

## Slide Objective
Communicate real, grounded benefits without overclaiming clinical or statistical outcomes.

## Main Heading
Impact & Benefits

## Subheading
Grounded in what the system actually does — not projected outcomes.

## Slide Content

**User Impact**
- Greater independence completing everyday digital tasks
- Reduced interaction friction
- Safer digital interaction (deliberate confirmation where it matters)
- More understandable interfaces
- Reduced need for assistance

**Accessibility Impact**
- Moves beyond static, manually-toggled accessibility settings
- Supports multiple functional requirements at once
- Context-aware adaptation, not a fixed mode
- Multimodal interaction (visual, voice, haptic)
- Personalizes interaction without changing the task's goal

**Technical Impact**
- Modular architecture (each concern is its own Django app)
- Deterministic, explainable barrier detection
- Approved adaptation catalogue (nothing applied outside it)
- Optional AI reasoning layered on top, never in sole control
- Independent safety validation on every applied change
- Measurable feedback loop, not an assumed improvement

**System Impact**
- The same core engine can support different digital environments
- Adaptation logic stays separate from business/task logic
- Environment and Ability Profile remain independent of each other
- Future environments can reuse the same reasoning layer

## Key Message
Every benefit here traces back to a real, working part of the system — not a projected statistic.

## Visual Suggestion
Four labeled columns/cards (User / Accessibility / Technical / System), each a short bullet list under its own icon.

## Canva Layout
Four equal-width vertical cards side by side, each with a category icon at top, category name, and 4–5 short bullets. Keep bullet phrasing under ~8 words each.

## Speaker Notes
"We were careful with this slide — no invented percentages, no clinical claims. Every one of these benefits is a direct consequence of something the system actually does: real barrier detection, real safety validation, real feedback collection. That's what makes it credible instead of just aspirational."

## Design Notes
Do not include any numeric claim (percentages, "X% improvement") on this slide — none are backed by real user-study data; keep benefits qualitative and directly traceable to real system behavior.

---

# SLIDE 13 — FUTURE SCOPE

## Slide Objective
Show ambition and scalability while being unambiguous about what's implemented today versus what's planned.

## Main Heading
Future Scope

## Subheading
Clearly separate from what's implemented in this prototype today.

## Slide Content
1. **Multi-environment deployment** — railway kiosks, hospital check-in, ATMs, government service kiosks, retail self-checkout, educational platforms, workplace software
2. **Computer vision** — detect physical layout, recognize controls, estimate contrast, identify interaction zones automatically
3. **Real hardware integration** — kiosk APIs, haptic hardware, accessible input devices, assistive switches
4. **Wearable / sensor integration** — context signals, fatigue signals, environmental information
5. **Personalized learning** — use feedback and interaction outcomes to improve adaptation ranking and learn preferences, with consent
6. **Standards / accessibility integration** — WCAG-aware environment analysis, accessibility metadata, device-level accessibility APIs
7. **Cross-platform AbilityOS SDK/API** — web, mobile, kiosks, desktop applications

## Key Message
The reasoning core is designed to outlive the ticket-kiosk demo — these are the directions it's built to grow into.

## Visual Suggestion
A roadmap-style horizontal timeline or a 7-tile grid, each tile clearly stamped "FUTURE SCOPE" so it's never confused with the current build.

## Canva Layout
7 tiles in a 4+3 or 3+4 grid, each with an icon, short title, and one supporting line. A persistent small "FUTURE SCOPE — not yet implemented" banner strip across the top of the whole slide.

## Speaker Notes
"To be direct: none of this is built yet. What is built is the reasoning core — Person, Task, Environment, Barrier, Adaptation, Safety — and that core is exactly what would extend into every one of these directions. We designed the boundary between the demo and the engine specifically so this list is a roadmap, not a rewrite."

## Design Notes
Use a visually distinct "not yet implemented" treatment for this whole slide (e.g., a dashed border theme, a slightly desaturated palette) so it can never be mistaken for a "current features" slide even out of context.

---

# SLIDE 14 — CONCLUSION / CALL TO ACTION

## Slide Objective
Close on the single sentence a judge should remember.

## Main Heading
Accessibility Should Adapt to People.

## Subheading
Not the other way around.

## Slide Content
- AbilityOS transforms **Person + Task + Environment** into **Barrier → Adaptation → Outcome**.
- *"We are not building another accessibility setting. We are building an adaptive interaction layer that helps digital systems respond to the person using them."*
- **ABILITYOS**
- *"Technology that adapts to the person — not the other way around."*

## Key Message
One reasoning layer, nine real profiles, one consistent proof: the barrier changes with the person — so the fix should too.

## Visual Suggestion
Minimal, almost entirely whitespace. The transformation line (Person+Task+Environment → Barrier→Adaptation→Outcome) centered, then the final quote beneath it, then the AbilityOS wordmark + tagline at the very bottom — mirroring Slide 1 to close the loop visually.

## Canva Layout
Single centered column, generous vertical spacing between the three text blocks (transformation line / mission quote / wordmark+tagline). No side visuals, no icon clutter — let the words carry the slide.

## Speaker Notes
"So — person, task, environment becomes barrier, adaptation, outcome. That's the whole system, in one line. We're not shipping another accessibility setting buried in a menu. We're proposing a layer that lets any digital system respond to the person actually using it. Thank you."

## Design Notes
Mirror Slide 1's exact typography and spacing for the closing wordmark/tagline so the deck visually "closes the loop." This is the one slide where less text is strictly better — resist adding anything beyond what's listed above.

---

# CANVA DESIGN SYSTEM

**Direction:** modern accessibility/human-computer-interaction technology — not a healthcare brochure, not a sterile enterprise SaaS deck.

**Feel:** AI + Accessibility + Human-Centered Technology.

**Color:**
- Base: clean white / very light gray background (`#FAFBFC`-ish)
- Primary accent: deep blue (`#1B3A6B`-ish) or teal (`#0F7A6D`-ish — matches the kiosk UI's own accent color)
- Secondary accent: a single warm highlight (amber/coral) used sparingly for "barrier"/"before" states only
- Avoid: red/green as a pure pass/fail signal (accessibility-unfriendly as a sole indicator); pair color with an icon or label always

**Shape & layout:**
- Rounded cards (12–16px radius equivalent), consistent across every slide
- Minimal gradients — flat fills with one soft shadow style, reused everywhere
- Simple line icons (one icon family for the whole deck — don't mix filled and outline styles)
- High contrast text (dark text on light backgrounds, or the reverse — never mid-gray on mid-gray)
- Large, readable typography — nothing under ~18pt-equivalent on-slide
- Generous spacing — no slide should feel dense; move detail to Speaker Notes instead

**Typography:**
- Title font: modern bold sans-serif (Poppins Bold / Sora Bold / Manrope Bold)
- Body font: clean readable sans-serif (Inter / Work Sans / IBM Plex Sans)
- Keep exactly two font families in the whole deck

**Consistency checklist:**
- Same heading size on every slide
- Same body text size on every slide
- Same card corner radius everywhere
- Same icon line-weight everywhere
- Same arrow style everywhere (all pipeline diagrams use the same arrowhead)
- Same spacing rhythm (pick one spacing unit and multiply it, don't eyeball gaps)

**Canva search keywords to use:**
"accessibility technology" · "adaptive interface" · "human computer interaction" · "AI accessibility" · "digital inclusion" · "assistive technology" · "smart kiosk" · "AI healthcare technology"

No external/custom assets are required — everything above is achievable with Canva's built-in icon and illustration library.

---

# VISUAL STORYBOARD

| Slide | Main Visual | Purpose |
|---|---|---|
| 1 | Human + adaptive interface reshaping around them | Introduce vision |
| 2 | Person/system mismatch equation + 9 barrier icon chips | Establish the problem |
| 3 | Static vs. adaptive flow diagrams + comparison table | Explain the structural gap |
| 4 | 6-step Person→Outcome pipeline + "current demo" tag | Introduce the solution |
| 5 | 12-stage vertical pipeline diagram | Explain the full workflow |
| 6 | Scoring formula card + "LLM proposes, rule engine disposes" pull-quote | Explain the reasoning engine |
| 7 | 8-category technology card grid | Establish technical credibility |
| 8 | Layered architecture diagram (Frontend/API/Core/DB) | Explain the implementation |
| 9 | Kiosk illustration with 3 person→barrier→adaptation branches | Demonstrate the proof-of-concept |
| 10 | 3×3 persona card grid | Show breadth/adaptability |
| 11 | Split-screen standard vs. adaptive kiosk | Show visible transformation |
| 12 | 4-column impact card grid | Explain benefits |
| 13 | 7-tile future roadmap grid | Show scalability |
| 14 | Minimal centered closing statement | Leave a memorable message |

---

# JUDGE TALKING POINTS

1. "AbilityOS is not the kiosk; the kiosk is our controlled demonstration environment."
2. "The problem we solve is the mismatch between a person's functional abilities and the demands of a digital environment — not a medical condition."
3. "We detect barriers rather than simply enabling predefined accessibility modes."
4. "The same task, on the same kiosk, produces a different barrier and a different adaptation depending on who's using it."
5. "The backend remains the source of truth — the frontend never calculates a barrier, a score, or a safety decision."
6. "AI is optional and constrained by deterministic rules and independent safety validation."
7. "The LLM proposes; the rule engine disposes."
8. "We separate the accessibility reasoning layer from the application's business logic — the task itself never changes."
9. "Feedback gives us measurable evidence about whether an adaptation actually helped, instead of assuming a UI change is automatically an improvement."
10. "Nine functional profiles run through the exact same engine — no special-case code per profile."
11. "Every adaptation is drawn from one approved catalogue and validated before it's ever applied."
12. "The long-term vision is to make AbilityOS reusable across many digital environments, not just this one kiosk."

---

# 30-SECOND PITCH

"AbilityOS is an adaptive accessibility reasoning layer — an operating system for human abilities. The problem it solves: the same digital interface doesn't work equally well for everyone, and today's fix is usually a static, manually-toggled accessibility setting. AbilityOS instead watches the person, the task, and the environment together, detects the actual functional barrier between them, and applies the smallest safe adaptation to remove it — without changing what the task is. We're demonstrating it through a ticket-purchase kiosk with nine real functional profiles, but the reasoning layer itself is built to work behind any digital interaction."

---

# 60-SECOND PITCH

"**Problem:** Digital interfaces assume one average user. Small touch targets, audio-only alerts, too many choices, short response windows — these aren't medical conditions, they're functional mismatches between a real person and a specific environment, and today's accessibility settings are static switches someone has to find and turn on themselves.

**Solution:** AbilityOS is an adaptive accessibility reasoning layer. It keeps a consented, functional Ability Profile, watches the task someone is trying to complete, compares that against the current environment, detects the specific barrier, and selects the smallest useful adaptation — all scored on accessibility benefit, task relevance, user preference, confidence, cost, and risk, then checked by an independent safety validator before anything is applied.

**Technology:** A Django REST backend running deterministic barrier detection and adaptation scoring, an optional AI layer that can rank or explain approved candidates but never invent one, and a React kiosk frontend that only ever renders backend-approved changes.

**Demo:** One ticket-purchase kiosk, nine functional profiles — low vision, hearing difficulty, cognitive load, limited mobility, speech difficulty, fatigue, slower reaction speed, combined visual-and-hearing needs, and high interaction sensitivity — each producing its own real, verified barrier and adaptation from the exact same engine.

**Impact:** Greater independence, less interaction friction, and a measurable feedback loop instead of an assumed improvement.

**Future:** The same reasoning core, extended to real kiosks, ATMs, check-in systems, and beyond — accessibility as a reusable layer, not a one-off feature."

---

# 2-MINUTE DEMO SCRIPT

**0:00–0:20 — Introduce the problem**
"Every one of us has hit a digital interface that didn't quite work for us in the moment — a button too small, an alert we couldn't hear, too many choices on one screen. These are functional mismatches between a person and an environment, not something wrong with the person. Today, the usual fix is a static accessibility setting someone has to find and switch on themselves."

**0:20–0:40 — Introduce AbilityOS**
"AbilityOS is an adaptive accessibility reasoning layer — an operating system for human abilities. It watches three things together: the person's functional Ability Profile, the task they're doing, and the environment they're in — and from that comparison, it decides if there's a real barrier worth fixing."

**0:40–1:00 — Person + Task + Environment**
"Here's our demo: a public ticket-purchase kiosk. Same task every time — select a destination, a ticket type, a quantity, confirm — same environment. Watch what happens as I change only the person."

**1:00–1:30 — Show a profile and detected barrier**
"I'll select the Low Vision + Reduced Dexterity profile, give consent, and let AbilityOS analyze the task and environment. It detects two real barriers — small tap targets and low contrast — with a plain-language explanation of why, not just a label."

**1:30–1:50 — Show the adaptation being applied**
"AbilityOS scores the approved candidates, an independent safety check approves the result, and now — watch the kiosk — the controls are larger and the contrast is higher. Same task. I can complete the exact same purchase, just without fighting the interface to do it."

**1:50–2:00 — Outcome and scalability**
"That's one profile. We have nine, all running through this same engine, and a feedback and analytics loop turning every session into real evidence. The kiosk is just where we're proving it — the reasoning layer underneath is what scales."

---

# KEY DIFFERENTIATORS

1. **Person + Task + Environment reasoning, not profile-only reasoning.** A barrier is only ever declared from a real mismatch between all three — the same profile can be barrier-free in one environment and blocked in another, which is what makes the detection genuinely explainable rather than a lookup table.

2. **Barrier-first architecture.** The system doesn't ask "which accessibility mode should I turn on for this user type" — it asks "is there an actual mismatch right now," which is why it can correctly detect *nothing* to fix when the environment already resolves the need.

3. **One approved adaptation catalogue, shared by every profile.** Nine functional profiles, zero duplicated adaptation logic — a new profile can go live by extending existing catalogue entries' `resolves_barrier_types`, not by writing new UI code.

4. **Deterministic core with optional AI on top.** The full pipeline — detection, scoring, safety — works with zero AI configuration. AI, when enabled, is strictly a ranking/explanation layer, never the decision-maker: this matters because it means the system's core behavior is testable, predictable, and never dependent on an external API being available.

5. **Independent, non-bypassable safety validation.** Every adaptation passes through a validator that checks it against an explicit allow-list before it can change anything on screen — accessibility changes can never modify business logic (ticket price, transaction state) as a side effect.

6. **Business logic and accessibility logic are fully separated.** The ticket-purchase task's four required steps never change; only how much time, how much spacing, or what modality the interaction offers changes. This is what lets the demo prove "same task, different adaptation" instead of "different task per profile."

7. **A real feedback and evidence loop, not an assumed improvement.** Every session's outcome, events, and feedback feed a Learning Signal — structured evidence that an adaptation helped (or didn't), rather than a UI change the system just assumes was beneficial.

---

# CURRENT LIMITATIONS

Framed as the boundary between the **current prototype** and **future deployment** — not as weaknesses to hide.

- The current demo runs on one controlled kiosk environment (`kiosk_standard`) and one task (`purchase_ticket`) — real-world deployment would require integration with each target system's actual physical/software environment.
- Computer-vision environment analysis (OpenCV + OCR) is implemented but optional and off by default; the demo relies on structured JSON environment data rather than live camera input.
- The AI Decision Engine is optional — with no provider key configured, every decision is still made, but through the deterministic scoring formula rather than an LLM.
- The Learning Signal is currently evidence collection — it produces structured, readable evidence per session, but nothing yet automatically consumes that evidence to improve future recommendations.
- Real-world accessibility effectiveness would need evaluation with real users over real sessions — the current results are demonstration-session outcomes, not a validated study.
- Production deployment would need its own security/privacy review, login flow, and infrastructure hardening beyond what a login-free hackathon demo requires today.
- The barrier and adaptation catalogues cover 10 barrier types and 16 adaptations across 9 functional profiles — a meaningful range for the demo, not an exhaustive accessibility taxonomy.

---

# FINAL VERIFICATION NOTE

Every barrier name, adaptation name, task name, environment name, persona count, API path, and technology in this document was checked directly against the AbilityOS repository (backend models/services, `seed_demo.py`, `requirements.txt`, `package.json`, `api/urls.py`, and the live barrier/adaptation engine) at the time this file was written — not copied from the original concept specification or an earlier draft.
