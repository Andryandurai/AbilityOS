"""Environment Understanding Engine (Phase 3).

`EnvironmentAnalyzer` describes what the current screen/physical context
looks like — facts only ("this button is 120x45px", "contrast is low").
It never judges whether those facts are a problem for any particular
person; that comparison against an Ability Profile is Phase 4's job.

Only `analyze_fixture()` is implemented in Phase 3, matching the project
spec's explicit allowance: "the hackathon environment to be simulated
through a JSON fixture." `analyze_screenshot()` and `analyze_camera()` are
real methods on this interface — not omitted — so a future phase can plug
in computer vision without changing this module's shape, but they raise
`NotImplementedError` here rather than pretending to produce results.

(Note: `ai_engine.services.vision_service` is a separate, pre-existing,
optional screenshot-analysis path that already powers the working kiosk
demo's environment step when `VISION_ENABLED=true`. This class doesn't
call into it — Phase 3's own interface is deliberately kept to a clean
fixture-only implementation, per this phase's explicit scope.)
"""

from __future__ import annotations

import json
from pathlib import Path

from environments.models import Environment

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


class EnvironmentNotFoundError(LookupError):
    """Raised for an unknown environment_id."""


class EnvironmentAnalyzer:
    @staticmethod
    def analyze_fixture(environment_id: str) -> dict:
        """Deterministic lookup: environment_id -> EnvironmentDescriptor.

        Checks the database first (what `seed_demo` populates); falls back
        to reading the JSON file directly under environments/fixtures/ so
        the fixture is usable even before a `migrate`+`seed_demo` has run.
        Never invents an environment for an unknown id.
        """

        if not environment_id:
            raise EnvironmentNotFoundError("environment_id is required.")

        env = Environment.objects.filter(environment_id=environment_id).first()
        if env is not None:
            return env.data

        fixture_path = FIXTURES_DIR / f"{environment_id}.json"
        if fixture_path.exists():
            with open(fixture_path, "r", encoding="utf-8") as f:
                return json.load(f)

        raise EnvironmentNotFoundError(f"Unknown environment_id '{environment_id}'.")

    @staticmethod
    def analyze_screenshot(image_base64: str) -> dict:
        raise NotImplementedError("Environment source 'screenshot' is not implemented in Phase 3.")

    @staticmethod
    def analyze_camera(frame) -> dict:
        raise NotImplementedError("Environment source 'camera' is not implemented in Phase 3.")
