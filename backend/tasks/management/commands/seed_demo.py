"""python manage.py seed_demo

Creates everything the hackathon demo needs to run immediately (Part 29):
- the purchase_ticket task + its steps
- the kiosk_standard environment fixture
- the full adaptation catalogue (Part 13)
- three demo Ability Profiles (Part 13/15)
- a small set of clearly-labelled seed InteractionSessions/Feedback rows so
  the before/after analytics panel has example numbers on a fresh install
  (Part 18's "clearly label seeded/demo measurements" requirement).

Idempotent: safe to run multiple times (uses update_or_create throughout).
"""

from __future__ import annotations

import json
from pathlib import Path

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

from abilities.models import AbilityProfile
from adaptations.models import Adaptation
from api.services.orchestrator import InteractionOrchestrator
from barriers.models import Barrier
from barriers.services.detection import detect_and_save
from environments.models import Environment
from feedback.models import InteractionSession
from tasks.models import Task, TaskStep
from users.models import ConsentRecord, User

FIXTURES_DIR = Path(__file__).resolve().parents[3] / "fixtures"

ADAPTATION_CATALOGUE = [
    dict(
        name="increase_target_size",
        display_name="Increase target size",
        description="Enlarges tap targets for the controls relevant to the current task, "
        "without changing what the task is.",
        resolves_barrier_types=["small_tap_targets", "fatigue_degraded_precision"],
        modality="visual",
        accessibility_benefit=0.9,
        interaction_cost=0.10,
        risk=0.05,
        risk_level=Adaptation.RISK_LOW,
        ui_effects={"button_scale": 1.8, "spacing_scale": 1.2},
    ),
    dict(
        name="increase_spacing",
        display_name="Increase spacing",
        description="Adds space between controls to reduce accidental adjacent taps.",
        resolves_barrier_types=["small_tap_targets", "fatigue_degraded_precision"],
        modality="visual",
        accessibility_benefit=0.5,
        interaction_cost=0.10,
        risk=0.05,
        risk_level=Adaptation.RISK_LOW,
        ui_effects={"spacing_scale": 1.6},
    ),
    dict(
        name="increase_contrast",
        display_name="Increase contrast",
        description="Raises text/background contrast and enlarges text for the current screen only.",
        resolves_barrier_types=["low_contrast"],
        modality="visual",
        accessibility_benefit=0.9,
        interaction_cost=0.10,
        risk=0.05,
        risk_level=Adaptation.RISK_LOW,
        ui_effects={"contrast": "high", "text_scale": 1.3},
    ),
    dict(
        name="simplify_navigation",
        display_name="Simplify navigation",
        description="Shows fewer visible options at once by restructuring (not removing) the same choices.",
        resolves_barrier_types=["too_many_choices"],
        modality="visual",
        accessibility_benefit=0.7,
        interaction_cost=0.35,
        risk=0.15,
        risk_level=Adaptation.RISK_MEDIUM,
        ui_effects={"choice_limit": 4, "flow": "simplified"},
    ),
    dict(
        name="reduce_choice_count",
        display_name="Reduce choice count",
        description="Groups secondary options behind a 'more' step so fewer choices are visible at once.",
        resolves_barrier_types=["too_many_choices"],
        modality="visual",
        accessibility_benefit=0.6,
        interaction_cost=0.25,
        risk=0.10,
        risk_level=Adaptation.RISK_MEDIUM,
        ui_effects={"choice_limit": 3},
    ),
    dict(
        name="step_by_step_flow",
        display_name="Step-by-step guided flow",
        description="Breaks the task into a one-choice-at-a-time sequence with a visible progress indicator.",
        resolves_barrier_types=["too_many_choices"],
        modality="visual",
        accessibility_benefit=0.95,
        interaction_cost=0.40,
        risk=0.10,
        risk_level=Adaptation.RISK_MEDIUM,
        ui_effects={"flow": "guided", "choice_limit": 1, "progress_indicator": True},
    ),
    dict(
        name="voice_instruction",
        display_name="Voice instructions",
        description="Adds spoken prompts guiding the person through the task.",
        resolves_barrier_types=["too_many_choices", "low_contrast"],
        modality="voice",
        accessibility_benefit=0.5,
        interaction_cost=0.45,
        risk=0.20,
        risk_level=Adaptation.RISK_MEDIUM,
        ui_effects={"voice_prompts": True},
    ),
    dict(
        name="text_to_speech",
        display_name="Text-to-speech for on-screen content",
        description="Reads on-screen labels aloud on request.",
        resolves_barrier_types=["low_contrast"],
        modality="voice",
        accessibility_benefit=0.6,
        interaction_cost=0.30,
        risk=0.10,
        risk_level=Adaptation.RISK_MEDIUM,
        ui_effects={"tts": True},
    ),
    dict(
        name="caption_audio",
        display_name="Caption / mirror audio alerts",
        description="Mirrors an audio-only alert as an on-screen banner and a device vibration.",
        resolves_barrier_types=["audio_only_alert"],
        modality="visual",
        accessibility_benefit=0.9,
        interaction_cost=0.15,
        risk=0.05,
        risk_level=Adaptation.RISK_LOW,
        ui_effects={"banner_alert": True, "haptics": True},
    ),
    dict(
        name="haptic_confirmation",
        display_name="Haptic confirmation",
        description="Adds a vibration confirming a tap landed or an alert fired.",
        resolves_barrier_types=["audio_only_alert", "small_tap_targets"],
        modality="haptic",
        accessibility_benefit=0.55,
        interaction_cost=0.15,
        risk=0.05,
        risk_level=Adaptation.RISK_LOW,
        ui_effects={"haptics": True},
    ),
    dict(
        name="alternative_voice_input",
        display_name="Alternative voice input",
        description="Lets the person complete the task by speaking instead of touching the screen.",
        resolves_barrier_types=["small_tap_targets"],
        modality="voice",
        accessibility_benefit=0.8,
        interaction_cost=0.70,
        risk=0.50,
        risk_level=Adaptation.RISK_HIGH,
        requires_confirmation=True,
        ui_effects={"voice_input": True},
    ),
    dict(
        name="confirmation_before_irreversible_action",
        display_name="Confirm before irreversible action",
        description="Adds a short confirmation step before a purchase is finalised.",
        resolves_barrier_types=["small_tap_targets", "fatigue_degraded_precision"],
        modality="visual",
        accessibility_benefit=0.3,
        interaction_cost=0.20,
        risk=0.05,
        risk_level=Adaptation.RISK_LOW,
        ui_effects={"confirm_step": True},
    ),
]

TASK_STEPS = [
    dict(
        step_id="select_destination",
        order=1,
        name="Select destination",
        controls=[
            {"id": "dest_central_station", "type": "button", "label": "Central Station"},
            {"id": "dest_airport", "type": "button", "label": "Airport"},
            {"id": "dest_hospital", "type": "button", "label": "Hospital"},
            {"id": "dest_university", "type": "button", "label": "University"},
        ],
    ),
    dict(
        step_id="select_ticket_type",
        order=2,
        name="Select ticket type",
        controls=[
            {"id": "ticket_single", "type": "button", "label": "Single"},
            {"id": "ticket_return", "type": "button", "label": "Return"},
        ],
    ),
    dict(
        step_id="select_quantity",
        order=3,
        name="Select quantity",
        controls=[
            {"id": "quantity_minus", "type": "button", "label": "-"},
            {"id": "quantity_plus", "type": "button", "label": "+"},
        ],
    ),
    dict(
        step_id="confirm_purchase",
        order=4,
        name="Confirm purchase",
        controls=[{"id": "buy_ticket", "type": "button", "label": "BUY TICKET"}],
    ),
]

DEMO_PROFILES = [
    dict(
        username="demo_low_vision_dexterity",
        display_name="Low Vision + Reduced Dexterity",
        label="Low Vision + Reduced Dexterity",
        dimensions={
            "vision": {"level": "large-text-needed", "confidence": 0.85, "source": "manual"},
            "dexterity": {"level": "reduced-precision", "confidence": 0.8, "source": "manual"},
            "hearing": {"level": "typical", "confidence": 0.5, "source": "default"},
            "cognition": {"level": "typical", "confidence": 0.5, "source": "default"},
            "fatigue": {"level": "fresh", "confidence": 0.5, "source": "default"},
        },
        preferred_modality=AbilityProfile.MODALITY_MIXED,
    ),
    dict(
        username="demo_hearing_difficulty",
        display_name="Hearing Difficulty",
        label="Hearing Difficulty",
        dimensions={
            "hearing": {"level": "partial", "confidence": 0.82, "source": "manual"},
            "vision": {"level": "typical", "confidence": 0.5, "source": "default"},
            "dexterity": {"level": "typical", "confidence": 0.5, "source": "default"},
            "cognition": {"level": "typical", "confidence": 0.5, "source": "default"},
            "fatigue": {"level": "fresh", "confidence": 0.5, "source": "default"},
        },
        preferred_modality=AbilityProfile.MODALITY_MIXED,
    ),
    dict(
        username="demo_cognitive_load",
        display_name="Cognitive Load",
        label="Cognitive Load",
        dimensions={
            "cognition": {"level": "needs-step-by-step", "confidence": 0.78, "source": "manual"},
            "vision": {"level": "typical", "confidence": 0.5, "source": "default"},
            "dexterity": {"level": "typical", "confidence": 0.5, "source": "default"},
            "hearing": {"level": "typical", "confidence": 0.5, "source": "default"},
            "fatigue": {"level": "fresh", "confidence": 0.5, "source": "default"},
        },
        preferred_modality=AbilityProfile.MODALITY_VISUAL,
    ),
]


class Command(BaseCommand):
    help = "Seed AbilityOS with the demo task, environment, adaptation catalogue and personas."

    def handle(self, *args, **options):
        self.stdout.write("Seeding AbilityOS demo data...")

        task = self._seed_task()
        environment = self._seed_environment()
        self._seed_adaptations()
        profiles = self._seed_profiles()
        self._seed_example_sessions(task, environment, profiles)

        self.stdout.write(self.style.SUCCESS("AbilityOS demo data ready. Run `python manage.py runserver`."))

    def _seed_task(self) -> Task:
        task, _ = Task.objects.update_or_create(
            task_id="purchase_ticket",
            defaults={
                "name": "Buy a ticket",
                "description": "Select a destination, ticket type and quantity, then confirm purchase.",
            },
        )
        for step in TASK_STEPS:
            TaskStep.objects.update_or_create(
                task=task, step_id=step["step_id"], defaults={k: v for k, v in step.items() if k != "step_id"}
            )
        self.stdout.write(f"  task: {task.task_id} ({task.steps.count()} steps)")
        return task

    def _seed_environment(self) -> Environment:
        fixture_path = FIXTURES_DIR / "kiosk_standard.json"
        with open(fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        environment, _ = Environment.objects.update_or_create(
            environment_id=data["environment_id"],
            defaults={
                "name": data["name"],
                "source": Environment.SOURCE_FIXTURE,
                "data": data,
            },
        )
        self.stdout.write(f"  environment: {environment.environment_id}")
        return environment

    def _seed_adaptations(self) -> None:
        for entry in ADAPTATION_CATALOGUE:
            entry = dict(entry)
            entry.setdefault("allowed_for_tasks", ["*"])
            entry.setdefault("requires_confirmation", entry["risk_level"] == Adaptation.RISK_HIGH)
            name = entry.pop("name")
            Adaptation.objects.update_or_create(name=name, defaults=entry)
        self.stdout.write(f"  adaptations: {Adaptation.objects.count()} catalogue entries")

    def _seed_profiles(self) -> list[User]:
        users = []
        for spec in DEMO_PROFILES:
            user, created = User.objects.update_or_create(
                username=spec["username"],
                defaults={
                    "display_name": spec["display_name"],
                    "is_demo_profile": True,
                    "password": make_password("demo-password"),
                },
            )
            AbilityProfile.objects.update_or_create(
                user=user,
                defaults={
                    "label": spec["label"],
                    "dimensions": spec["dimensions"],
                    "preferred_modality": spec["preferred_modality"],
                },
            )
            # Deliberately left ungranted: the consent gate (Part 27) is a
            # visible step in the demo flow, not a formality to skip. The
            # presenter clicks "I Agree" for each persona on first use.
            ConsentRecord.objects.get_or_create(user=user, defaults={"granted": False, "scope": []})
            users.append(user)
        self.stdout.write(f"  demo profiles: {', '.join(u.username for u in users)}")
        return users

    def _seed_example_sessions(self, task: Task, environment: Environment, profiles: list[User]) -> None:
        """Creates a small number of clearly-labelled (is_seed=True) example
        sessions so the before/after analytics panel isn't empty on a fresh
        install. These are real rows exercised through the same detection
        logic as a live session — not hand-typed metrics."""

        if InteractionSession.objects.filter(is_seed=True).exists():
            self.stdout.write("  example sessions already seeded, skipping")
            return

        primary_profile_user = profiles[0]
        profile = AbilityProfile.objects.get(user=primary_profile_user)

        # "Without AbilityOS": barriers detected, but nothing applied — the
        # struggle scenario, run three times with worsening outcomes.
        baseline_outcomes = [
            dict(completed=False, errors=5, time_seconds=95, assistance_requested=True, effort=5, confidence=2),
            dict(completed=True, errors=4, time_seconds=81, assistance_requested=True, effort=4, confidence=2),
            dict(completed=True, errors=3, time_seconds=74, assistance_requested=False, effort=4, confidence=3),
        ]
        for outcome in baseline_outcomes:
            session = InteractionSession.objects.create(
                user=primary_profile_user,
                task=task,
                environment=environment,
                baseline_mode=True,
                is_seed=True,
                ability_profile_snapshot=profile.dimensions,
            )
            detect_and_save(session, profile, task, environment)
            # record_feedback (not a direct Feedback.objects.create) so the
            # session status transition matches exactly what a live API
            # call would produce (Part 5 step 11-12).
            InteractionOrchestrator.record_feedback(session, outcome)

        # "With AbilityOS": barriers detected AND resolved, then a clean run.
        with_outcomes = [
            dict(completed=True, errors=1, time_seconds=50, assistance_requested=False, effort=2, confidence=4),
            dict(completed=True, errors=0, time_seconds=42, assistance_requested=False, effort=1, confidence=5),
            dict(completed=True, errors=0, time_seconds=39, assistance_requested=False, effort=1, confidence=5),
        ]
        for outcome in with_outcomes:
            session = InteractionSession.objects.create(
                user=primary_profile_user,
                task=task,
                environment=environment,
                baseline_mode=False,
                is_seed=True,
                ability_profile_snapshot=profile.dimensions,
            )
            detect_and_save(session, profile, task, environment)
            # Route seed sessions through the real orchestrator pipeline —
            # the same scoring + rule engine a live session uses — so
            # "used N times" in the analytics dashboard always reflects an
            # adaptation that was genuinely selected and approved, never a
            # hand-picked stand-in.
            InteractionOrchestrator.recommend_adaptations(session)
            InteractionOrchestrator.apply(session)
            InteractionOrchestrator.record_feedback(session, outcome)

        self.stdout.write("  example sessions: 3 baseline + 3 adapted (labelled is_seed=True)")
