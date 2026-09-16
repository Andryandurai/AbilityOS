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

    def test_seated_reach_with_control_outside_zone_triggers_controls_out_of_reach(self):
        dims = dims_with({"reach": {"level": "seated", "confidence": 0.82, "source": "manual"}})
        env = dict(
            STANDARD_KIOSK_ENV,
            controls=[{"id": "buy_ticket", "width": 120, "height": 40, "primary": True, "x": 1100, "y": 60}],
            interaction_zone={"x": 40, "y": 420, "width": 500, "height": 300},
        )

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertIn(Barrier.TYPE_CONTROLS_OUT_OF_REACH, types)

    def test_typical_reach_does_not_trigger_controls_out_of_reach(self):
        env = dict(
            STANDARD_KIOSK_ENV,
            controls=[{"id": "buy_ticket", "width": 120, "height": 40, "primary": True, "x": 1100, "y": 60}],
            interaction_zone={"x": 40, "y": 420, "width": 500, "height": 300},
        )

        barriers = detect_barriers(default_dimensions(), {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_CONTROLS_OUT_OF_REACH, types)

    def test_control_within_zone_does_not_trigger_controls_out_of_reach(self):
        dims = dims_with({"reach": {"level": "seated", "confidence": 0.82, "source": "manual"}})
        env = dict(
            STANDARD_KIOSK_ENV,
            controls=[{"id": "buy_ticket", "width": 120, "height": 40, "primary": True, "x": 200, "y": 500}],
            interaction_zone={"x": 40, "y": 420, "width": 500, "height": 300},
        )

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_CONTROLS_OUT_OF_REACH, types)

    def test_no_interaction_zone_or_position_data_does_not_trigger_controls_out_of_reach(self):
        """Regression guard: STANDARD_KIOSK_ENV (used by every other test in
        this file) has no x/y or interaction_zone — the new rule must stay
        a true no-op for every existing environment shape."""
        dims = dims_with({"reach": {"level": "seated", "confidence": 0.82, "source": "manual"}})

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, STANDARD_KIOSK_ENV)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_CONTROLS_OUT_OF_REACH, types)

    def test_limited_speech_with_voice_control_triggers_voice_only_input(self):
        dims = dims_with({"speech": {"level": "limited", "confidence": 0.8, "source": "manual"}})
        env = dict(
            STANDARD_KIOSK_ENV,
            controls=STANDARD_KIOSK_ENV["controls"]
            + [{"id": "voice_destination", "interaction_type": "voice", "label": "Speak your destination"}],
        )

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertIn(Barrier.TYPE_VOICE_ONLY_INPUT, types)

    def test_typical_speech_does_not_trigger_voice_only_input(self):
        """Negative case (section 21): the same voice-offering environment
        must NOT produce the barrier for a typical-speech profile — this is
        a real mismatch check, not `if profile == speech_difficulty`."""
        env = dict(
            STANDARD_KIOSK_ENV,
            controls=STANDARD_KIOSK_ENV["controls"]
            + [{"id": "voice_destination", "interaction_type": "voice", "label": "Speak your destination"}],
        )

        barriers = detect_barriers(default_dimensions(), {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_VOICE_ONLY_INPUT, types)

    def test_limited_speech_without_voice_control_does_not_trigger_barrier(self):
        """Regression guard: STANDARD_KIOSK_ENV (every other test in this
        file) has no voice-interaction control — the rule must stay a
        true no-op there even for a limited-speech profile."""
        dims = dims_with({"speech": {"level": "limited", "confidence": 0.8, "source": "manual"}})

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, STANDARD_KIOSK_ENV)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_VOICE_ONLY_INPUT, types)

    def test_high_fatigue_with_multi_step_flow_triggers_excessive_interaction_burden(self):
        dims = dims_with({"fatigue": {"level": "high", "confidence": 0.8, "source": "manual"}})
        env = dict(STANDARD_KIOSK_ENV, interaction_step_count=4)

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertIn(Barrier.TYPE_EXCESSIVE_INTERACTION_BURDEN, types)

    def test_fresh_fatigue_does_not_trigger_excessive_interaction_burden(self):
        """Negative case: the same multi-step environment must NOT produce
        the barrier for a fresh/typical fatigue profile — a real mismatch
        check, not `if profile == fatigue_reduced_stamina`."""
        env = dict(STANDARD_KIOSK_ENV, interaction_step_count=4)

        barriers = detect_barriers(default_dimensions(), {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_EXCESSIVE_INTERACTION_BURDEN, types)

    def test_high_fatigue_with_comfortable_step_count_does_not_trigger_barrier(self):
        """A short flow is not itself a barrier — only a mismatch with a
        reduced-stamina profile above the comfortable step threshold."""
        dims = dims_with({"fatigue": {"level": "high", "confidence": 0.8, "source": "manual"}})
        env = dict(STANDARD_KIOSK_ENV, interaction_step_count=3)

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_EXCESSIVE_INTERACTION_BURDEN, types)

    def test_high_fatigue_without_step_count_fact_does_not_trigger_barrier(self):
        """Regression guard: STANDARD_KIOSK_ENV (every other test in this
        file) has no interaction_step_count fact at all — the rule must
        stay a true no-op there even for a high-fatigue profile."""
        dims = dims_with({"fatigue": {"level": "high", "confidence": 0.8, "source": "manual"}})

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, STANDARD_KIOSK_ENV)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_EXCESSIVE_INTERACTION_BURDEN, types)

    # Step 26's four mandatory negative-case scenarios, verified directly.
    def test_case1_typical_reaction_speed_with_short_timeout_no_barrier(self):
        env = dict(STANDARD_KIOSK_ENV, confirmation_timeout_seconds=5)

        barriers = detect_barriers(default_dimensions(), {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_TIME_LIMITED_INTERACTION, types)

    def test_case2_slower_reaction_speed_with_short_timeout_triggers_barrier(self):
        dims = dims_with({"reaction_speed": {"level": "slower", "confidence": 0.8, "source": "manual"}})
        env = dict(STANDARD_KIOSK_ENV, confirmation_timeout_seconds=5)

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertIn(Barrier.TYPE_TIME_LIMITED_INTERACTION, types)

    def test_case3_slower_reaction_speed_with_generous_timeout_no_barrier(self):
        dims = dims_with({"reaction_speed": {"level": "slower", "confidence": 0.8, "source": "manual"}})
        env = dict(STANDARD_KIOSK_ENV, confirmation_timeout_seconds=30)

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_TIME_LIMITED_INTERACTION, types)

    def test_case4_requirement_exactly_met_by_environment_no_mismatch(self):
        """Slower reaction speed requires 10 seconds; an environment
        configured with exactly 10 seconds is not a mismatch (a boundary
        case, not just a smaller-generosity case than CASE 3)."""
        dims = dims_with({"reaction_speed": {"level": "slower", "confidence": 0.8, "source": "manual"}})
        env = dict(STANDARD_KIOSK_ENV, confirmation_timeout_seconds=10)

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_TIME_LIMITED_INTERACTION, types)

    def test_slower_reaction_speed_without_timeout_fact_does_not_trigger_barrier(self):
        """Regression guard: STANDARD_KIOSK_ENV (every other test in this
        file) has no confirmation_timeout_seconds fact at all — the rule
        must stay a true no-op there even for a slower-reaction profile."""
        dims = dims_with({"reaction_speed": {"level": "slower", "confidence": 0.8, "source": "manual"}})

        barriers = detect_barriers(dims, {"task_id": "purchase_ticket"}, STANDARD_KIOSK_ENV)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_TIME_LIMITED_INTERACTION, types)

    # Phase 5 (Visual + Hearing Support) section 17: both barriers this
    # profile relies on already exist and are already covered above in
    # isolation; these tests specifically cover the combined profile and
    # the environment-driven negative cases the request calls out.
    def _visual_hearing_dims(self):
        return dims_with(
            {
                "vision": {"level": "low-contrast-sensitive", "confidence": 0.8, "source": "manual"},
                "hearing": {"level": "relies-on-visual", "confidence": 0.8, "source": "manual"},
            }
        )

    def test_visual_hearing_profile_gets_both_barriers_on_standard_kiosk(self):
        barriers = detect_barriers(self._visual_hearing_dims(), {"task_id": "purchase_ticket"}, STANDARD_KIOSK_ENV)

        types = [b.barrier_type for b in barriers]
        self.assertIn(Barrier.TYPE_AUDIO_ONLY_ALERT, types)
        self.assertIn(Barrier.TYPE_LOW_CONTRAST, types)

    def test_visual_hearing_profile_with_mirrored_alert_does_not_trigger_audio_barrier(self):
        """TEST 3: a visual/captioned alert already available means there is
        no mismatch left to detect — the barrier must not fire even though
        the profile's hearing requirement is unchanged."""
        env = dict(STANDARD_KIOSK_ENV, visual_alert_mirror=True)

        barriers = detect_barriers(self._visual_hearing_dims(), {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_AUDIO_ONLY_ALERT, types)
        self.assertIn(Barrier.TYPE_LOW_CONTRAST, types)

    def test_visual_hearing_profile_with_adequate_contrast_does_not_trigger_contrast_barrier(self):
        """TEST 4: adequate contrast means there is no mismatch left to
        detect for the vision requirement."""
        env = dict(STANDARD_KIOSK_ENV, contrast=0.95)

        barriers = detect_barriers(self._visual_hearing_dims(), {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_LOW_CONTRAST, types)
        self.assertIn(Barrier.TYPE_AUDIO_ONLY_ALERT, types)

    def test_visual_hearing_profile_with_both_resolved_detects_nothing(self):
        """TEST 6 companion: once the environment already provides both a
        visual alert mirror and adequate contrast, nothing is left to
        recommend an adaptation for — the engine must not manufacture a
        barrier (and therefore not an adaptation) where none exists."""
        env = dict(STANDARD_KIOSK_ENV, visual_alert_mirror=True, contrast=0.95)

        barriers = detect_barriers(self._visual_hearing_dims(), {"task_id": "purchase_ticket"}, env)

        self.assertEqual(barriers, [])

    # Phase 6 (High Interaction Sensitivity) section 20's mandatory negative
    # cases, verified directly against detect_barriers.
    def _high_sensitivity_dims(self):
        return dims_with(
            {"interaction_sensitivity": {"level": "high", "confidence": 0.8, "source": "manual"}}
        )

    def test_case1_crowded_controls_triggers_accidental_activation_risk(self):
        env = dict(STANDARD_KIOSK_ENV, min_control_spacing_px=20, confirmation_available=True)

        barriers = detect_barriers(self._high_sensitivity_dims(), {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertIn(Barrier.TYPE_ACCIDENTAL_ACTIVATION_RISK, types)

    def test_case2_missing_confirmation_alone_triggers_barrier(self):
        """TEST 2: even with comfortable spacing, a consequential action
        with no confirmation step is its own real mismatch for this
        profile."""
        env = dict(STANDARD_KIOSK_ENV, min_control_spacing_px=50, confirmation_available=False)

        barriers = detect_barriers(self._high_sensitivity_dims(), {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertIn(Barrier.TYPE_ACCIDENTAL_ACTIVATION_RISK, types)

    def test_case3_well_separated_and_confirmed_detects_nothing(self):
        env = dict(STANDARD_KIOSK_ENV, min_control_spacing_px=50, confirmation_available=True)

        barriers = detect_barriers(self._high_sensitivity_dims(), {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_ACCIDENTAL_ACTIVATION_RISK, types)

    def test_case4_typical_sensitivity_with_crowded_kiosk_detects_nothing(self):
        env = dict(STANDARD_KIOSK_ENV, min_control_spacing_px=10, confirmation_available=False)

        barriers = detect_barriers(default_dimensions(), {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertNotIn(Barrier.TYPE_ACCIDENTAL_ACTIVATION_RISK, types)

    def test_high_sensitivity_with_no_spacing_fact_still_flags_missing_confirmation(self):
        """`confirmation_available` defaults to False when absent -- a real,
        honest default (no environment in this codebase currently bakes in
        confirmation), so the barrier still fires on that cause alone even
        when no spacing fact exists at all (spacing contributes nothing,
        confidence stays single-cause severity)."""
        env = dict(STANDARD_KIOSK_ENV)
        env.pop("min_control_spacing_px", None)

        barriers = detect_barriers(self._high_sensitivity_dims(), {"task_id": "purchase_ticket"}, env)

        types = [b.barrier_type for b in barriers]
        self.assertIn(Barrier.TYPE_ACCIDENTAL_ACTIVATION_RISK, types)
        self.assertEqual(barriers[0].severity, 0.6)  # single cause only (no spacing fact at all)
