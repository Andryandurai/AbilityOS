"""python manage.py seed_questionnaire

Seeds version 1 of the functional ability questionnaire (Phase 2).

IMPORTANT — kept in sync by hand with
frontend/src/constants/abilityProfile.js::ABILITY_QUESTIONS: the frontend's
manual profile editor and this questionnaire ask the same 10 functional
questions, in the same order, with the same option text, because they both
ultimately write the same abilities.constants.ALLOWED_LEVELS vocabulary. A
true single source of truth isn't practical across the Python/JS boundary
without a build-time codegen step (deliberately not added — see
docs/QUESTIONNAIRE.md's "known limitations"), so this file's QUESTIONS list
is the Python-side mirror of that same content, not a second, independently
invented question set. If a dimension's question text/options are edited in
one file, edit the other to match.

Idempotent: uses update_or_create keyed on (key, version), safe to re-run.
Does not touch the existing 9 demo profiles, task, or environment fixtures
-- entirely separate from tasks/management/commands/seed_demo.py.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from questionnaire.models import QuestionnaireQuestion

VERSION = 1

# Mirrors frontend/src/constants/abilityProfile.js::ABILITY_QUESTIONS
# exactly (key, question_text, option value/label pairs) -- see this
# file's module docstring.
QUESTIONS = [
    dict(
        key="vision",
        order=1,
        question_text="How comfortable are you reading small text?",
        options=[
            {"value": "typical", "label": "Comfortable"},
            {"value": "low-contrast-sensitive", "label": "I prefer higher contrast"},
            {"value": "large-text-needed", "label": "I need larger text"},
        ],
    ),
    dict(
        key="hearing",
        order=2,
        question_text="How well do audio alerts and sounds work for you?",
        options=[
            {"value": "typical", "label": "Audio works well for me"},
            {"value": "partial", "label": "I sometimes miss audio alerts"},
            {"value": "relies-on-visual", "label": "I rely on visual alerts instead"},
        ],
    ),
    dict(
        key="dexterity",
        order=3,
        question_text="How precise is touch interaction for you?",
        options=[
            {"value": "typical", "label": "Normal precision"},
            {"value": "reduced-precision", "label": "Precise tapping can be difficult"},
            {"value": "single-tap-only", "label": "I prefer single-tap interactions"},
        ],
    ),
    dict(
        key="reach",
        order=4,
        question_text="How easily can you reach controls in front of you?",
        options=[
            {"value": "full", "label": "I can reach everything comfortably"},
            {"value": "limited-upper", "label": "My upper reach is limited"},
            {"value": "seated", "label": "I'm usually seated"},
        ],
    ),
    dict(
        key="mobility",
        order=5,
        question_text="How easily can you move between steps of a task?",
        options=[
            {"value": "typical", "label": "I move around easily"},
            {"value": "limited", "label": "My movement is limited"},
            {"value": "stationary", "label": "I prefer to stay in one place"},
        ],
    ),
    dict(
        key="speech",
        order=6,
        question_text="How reliably can you use voice commands?",
        options=[
            {"value": "typical", "label": "Comfortable using my voice"},
            {"value": "limited", "label": "Speaking clearly can be difficult"},
            {"value": "unavailable", "label": "Voice isn't an option for me"},
        ],
    ),
    dict(
        key="cognition",
        order=7,
        question_text="How do you prefer choices to be presented?",
        options=[
            {"value": "typical", "label": "I am comfortable with many choices"},
            {"value": "prefers-fewer-choices", "label": "I prefer fewer choices"},
            {"value": "needs-step-by-step", "label": "I prefer one step at a time"},
        ],
    ),
    dict(
        key="fatigue",
        order=8,
        question_text="How is your energy right now?",
        options=[
            {"value": "fresh", "label": "Fresh"},
            {"value": "moderate", "label": "Somewhat tired"},
            {"value": "high", "label": "Very tired"},
        ],
    ),
    dict(
        key="reaction_speed",
        order=9,
        question_text="How quickly can you respond to on-screen prompts?",
        options=[
            {"value": "typical", "label": "Typical speed"},
            {"value": "slower", "label": "A bit slower"},
            {"value": "needs-extended-time", "label": "I need extra time"},
        ],
    ),
    dict(
        key="interaction_sensitivity",
        order=10,
        question_text="How do you prefer controls to behave?",
        options=[
            {"value": "typical", "label": "Typical interaction works for me"},
            {"value": "high", "label": "I prefer stable, well-separated, deliberate interactions"},
        ],
    ),
]


class Command(BaseCommand):
    help = "Seed version 1 of the AbilityOS functional ability questionnaire."

    def handle(self, *args, **options):
        self.stdout.write("Seeding AbilityOS questionnaire...")
        for q in QUESTIONS:
            QuestionnaireQuestion.objects.update_or_create(
                key=q["key"],
                version=VERSION,
                defaults={
                    "question_text": q["question_text"],
                    "question_type": QuestionnaireQuestion.SINGLE_CHOICE,
                    "order": q["order"],
                    "options": q["options"],
                },
            )
        self.stdout.write(self.style.SUCCESS(f"Questionnaire v{VERSION}: {len(QUESTIONS)} questions ready."))
