from django.test import TestCase

from abilities.models import default_dimensions
from barriers.models import Barrier
from barriers.services.detection import detect_barriers

STANDARD_KIOSK_ENV = {
    "controls": [{"id": "buy_ticket", "width": 120, "height": 40, "primary": True}],
    "contrast": 0.52,
    "visible_choice_count": 8,
    "audio_alert": True,
    "visual_alert_mirror": False,
}


def dims_with(overrides: dict) -> dict:
    dims = default_dimensions()
    dims.update(overrides)
    return dims


class BarrierDetectionTests(TestCase):
    def test_reduced_dexterity_with_small_targets_triggers_small_tap_targets(self):
        dims = dims_with({"dexterity": {"level": "reduced-precision", "confidence": 0.8, "source": "manual"}})

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, STANDARD_KIOSK_ENV)

        types = [b.barrier_type for b in barriers]
        self.assertIn(Barrier.TYPE_SMALL_TAP_TARGETS, types)

    def test_typical_dexterity_does_not_trigger_small_tap_targets(self):
        dims = default_dimensions()

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, STANDARD_KIOSK_ENV)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_SMALL_TAP_TARGETS, types)

    def test_low_vision_with_low_contrast_triggers_low_contrast_barrier(self):
        dims = dims_with({"vision": {"level": "large-text-needed", "confidence": 0.85, "source": "manual"}})

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, STANDARD_KIOSK_ENV)

        types = [b.barrier_type for b in barriers]
        self.assertIn(Barrier.TYPE_LOW_CONTRAST, types)

    def test_hearing_difficulty_with_audio_only_alert_triggers_barrier(self):
        dims = dims_with({"hearing": {"level": "partial", "confidence": 0.82, "source": "manual"}})

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, STANDARD_KIOSK_ENV)

        types = [b.barrier_type for b in barriers]
        self.assertIn(Barrier.TYPE_AUDIO_ONLY_ALERT, types)

    def test_mirrored_audio_alert_does_not_trigger_barrier(self):
        dims = dims_with({"hearing": {"level": "partial", "confidence": 0.82, "source": "manual"}})
        env = dict(STANDARD_KIOSK_ENV, visual_alert_mirror=True)

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_AUDIO_ONLY_ALERT, types)

    def test_cognitive_load_with_many_choices_triggers_too_many_choices(self):
        dims = dims_with({"cognition": {"level": "needs-step-by-step", "confidence": 0.78, "source": "manual"}})

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, STANDARD_KIOSK_ENV)

        types = [b.barrier_type for b in barriers]
        self.assertIn(Barrier.TYPE_TOO_MANY_CHOICES, types)

    def test_high_fatigue_degrades_precision_even_with_typical_baseline(self):
        dims = dims_with({"fatigue": {"level": "high", "confidence": 0.7, "source": "session_signal"}})

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, STANDARD_KIOSK_ENV)

        types = [b.barrier_type for b in barriers]
        self.assertIn(Barrier.TYPE_FATIGUE_DEGRADED_PRECISION, types)

    def test_no_barriers_for_fully_typical_profile_on_roomy_environment(self):
        dims = default_dimensions()
        roomy_env = {
            "controls": [{"id": "buy_ticket", "width": 200, "height": 120, "primary": True}],
            "contrast": 0.9,
            "visible_choice_count": 2,
            "audio_alert": False,
        }

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, roomy_env)

        self.assertEqual(barriers, [])

    def test_barriers_sorted_by_severity_descending(self):
        dims = dims_with(
            {
                "dexterity": {"level": "single-tap-only", "confidence": 0.9, "source": "manual"},
                "vision": {"level": "low-contrast-sensitive", "confidence": 0.6, "source": "manual"},
            }
        )

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, STANDARD_KIOSK_ENV)

        severities = [b.severity for b in barriers]
        self.assertEqual(severities, sorted(severities, reverse=True))
