from django.test import TestCase
from rest_framework.test import APIClient

from environments.models import Environment
from environments.services.analyzer import EnvironmentAnalyzer, EnvironmentNotFoundError


def make_ticket_kiosk_default():
    return Environment.objects.create(
        environment_id="ticket_kiosk_default",
        name="Ticket Kiosk — Default",
        source=Environment.SOURCE_FIXTURE,
        data={
            "environment_id": "ticket_kiosk_default",
            "environment_type": "kiosk",
            "screen": {"width": 1280, "height": 800, "dpi": 96},
            "controls": [
                {"id": "confirm_button", "x": 100, "y": 500, "width": 120, "height": 45, "label": "Confirm", "type": "button"}
            ],
            "contrast": {"level": "low", "background": "#ffffff", "foreground": "#777777"},
            "noise_level": "moderate",
            "lighting": "normal",
        },
    )


class EnvironmentAnalyzerTests(TestCase):
    """Phase 3 Environment Understanding Engine — facts only, no
    accessibility judgement of any kind."""

    def test_ticket_kiosk_default_exists_and_returns_descriptor(self):
        make_ticket_kiosk_default()

        descriptor = EnvironmentAnalyzer.analyze_fixture("ticket_kiosk_default")

        self.assertEqual(descriptor["environment_id"], "ticket_kiosk_default")

    def test_descriptor_contains_screen_metadata(self):
        make_ticket_kiosk_default()
        descriptor = EnvironmentAnalyzer.analyze_fixture("ticket_kiosk_default")
        self.assertIn("screen", descriptor)
        self.assertEqual(descriptor["screen"]["width"], 1280)
        self.assertEqual(descriptor["screen"]["height"], 800)

    def test_descriptor_contains_control_dimensions(self):
        make_ticket_kiosk_default()
        descriptor = EnvironmentAnalyzer.analyze_fixture("ticket_kiosk_default")
        self.assertTrue(len(descriptor["controls"]) > 0)
        control = descriptor["controls"][0]
        self.assertIn("width", control)
        self.assertIn("height", control)

    def test_descriptor_contains_contrast_information(self):
        make_ticket_kiosk_default()
        descriptor = EnvironmentAnalyzer.analyze_fixture("ticket_kiosk_default")
        self.assertIn("contrast", descriptor)

    def test_descriptor_contains_noise_information(self):
        make_ticket_kiosk_default()
        descriptor = EnvironmentAnalyzer.analyze_fixture("ticket_kiosk_default")
        self.assertIn("noise_level", descriptor)

    def test_descriptor_contains_lighting_information(self):
        make_ticket_kiosk_default()
        descriptor = EnvironmentAnalyzer.analyze_fixture("ticket_kiosk_default")
        self.assertIn("lighting", descriptor)

    def test_unknown_environment_raises_not_found(self):
        with self.assertRaises(EnvironmentNotFoundError):
            EnvironmentAnalyzer.analyze_fixture("does_not_exist")

    def test_falls_back_to_reading_the_json_file_when_db_row_is_absent(self):
        """The fixture is usable even before seed_demo has run — the
        analyzer reads the file under environments/fixtures/ directly."""

        self.assertFalse(Environment.objects.filter(environment_id="ticket_kiosk_default").exists())
        descriptor = EnvironmentAnalyzer.analyze_fixture("ticket_kiosk_default")
        self.assertEqual(descriptor["environment_id"], "ticket_kiosk_default")

    def test_fixture_loading_is_deterministic(self):
        make_ticket_kiosk_default()
        first = EnvironmentAnalyzer.analyze_fixture("ticket_kiosk_default")
        second = EnvironmentAnalyzer.analyze_fixture("ticket_kiosk_default")
        self.assertEqual(first, second)

    def test_screenshot_source_is_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            EnvironmentAnalyzer.analyze_screenshot("fake-base64")

    def test_camera_source_is_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            EnvironmentAnalyzer.analyze_camera(None)

    def test_descriptor_never_mentions_barriers_or_accessibility_judgements(self):
        make_ticket_kiosk_default()
        descriptor = EnvironmentAnalyzer.analyze_fixture("ticket_kiosk_default")

        serialized = str(descriptor).lower()
        for forbidden in ("barrier", "too small", "cannot use", "inaccessible"):
            self.assertNotIn(forbidden, serialized)


class EnvironmentAnalyzeAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        make_ticket_kiosk_default()

    def test_analyze_known_environment_by_id_returns_200(self):
        response = self.client.post(
            "/api/environment/analyze/", {"environment_id": "ticket_kiosk_default"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["environment_id"], "ticket_kiosk_default")

    def test_analyze_unknown_environment_returns_404(self):
        response = self.client.post(
            "/api/environment/analyze/", {"environment_id": "does_not_exist"}, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_analyze_with_neither_session_nor_environment_id_returns_400(self):
        response = self.client.post("/api/environment/analyze/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_error_response_does_not_leak_stack_trace(self):
        response = self.client.post(
            "/api/environment/analyze/", {"environment_id": "does_not_exist"}, format="json"
        )
        self.assertNotIn("Traceback", str(response.data))
