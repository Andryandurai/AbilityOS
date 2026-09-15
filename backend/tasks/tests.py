from django.test import TestCase
from rest_framework.test import APIClient

from tasks.models import Task, TaskStep
from tasks.services.task_service import TaskNotFoundError, get_task_descriptor


def make_purchase_ticket_task():
    task = Task.objects.create(task_id="purchase_ticket", name="Buy a ticket", description="Buy a ticket.")
    TaskStep.objects.create(
        task=task,
        step_id="select_destination",
        order=1,
        name="Select destination",
        description="Choose a destination.",
        required=True,
        controls=[{"id": "dest_airport", "type": "button", "label": "Airport", "interaction_type": "touch"}],
    )
    TaskStep.objects.create(
        task=task,
        step_id="select_ticket_type",
        order=2,
        name="Select ticket type",
        description="Choose a ticket type.",
        required=True,
        controls=[{"id": "ticket_single", "type": "button", "label": "Single", "interaction_type": "touch"}],
    )
    TaskStep.objects.create(
        task=task,
        step_id="confirm_purchase",
        order=3,
        name="Confirm purchase",
        description="Confirm the purchase.",
        required=True,
        controls=[{"id": "buy_ticket", "type": "button", "label": "Buy", "interaction_type": "touch"}],
    )
    return task


class TaskServiceTests(TestCase):
    """Phase 3 Task Understanding Engine — deterministic lookup only, no
    barrier judgement of any kind should appear in this output."""

    def test_purchase_ticket_exists_and_returns_valid_descriptor(self):
        make_purchase_ticket_task()

        descriptor = get_task_descriptor("purchase_ticket")

        self.assertEqual(descriptor["task_id"], "purchase_ticket")
        self.assertIn("name", descriptor)
        self.assertIn("description", descriptor)
        self.assertIn("time_limit_seconds", descriptor)

    def test_descriptor_contains_expected_steps_in_order(self):
        make_purchase_ticket_task()

        descriptor = get_task_descriptor("purchase_ticket")
        step_ids = [s["id"] for s in descriptor["steps"]]

        self.assertEqual(step_ids, ["select_destination", "select_ticket_type", "confirm_purchase"])
        for step in descriptor["steps"]:
            self.assertIn("required", step)
            self.assertIn("description", step)

    def test_descriptor_contains_flattened_controls(self):
        make_purchase_ticket_task()

        descriptor = get_task_descriptor("purchase_ticket")
        control_ids = {c["id"] for c in descriptor["controls"]}

        self.assertEqual(control_ids, {"dest_airport", "ticket_single", "buy_ticket"})

    def test_unknown_task_raises_task_not_found(self):
        with self.assertRaises(TaskNotFoundError):
            get_task_descriptor("does_not_exist")

    def test_empty_task_id_raises_task_not_found(self):
        with self.assertRaises(TaskNotFoundError):
            get_task_descriptor("")

    def test_registry_lookup_is_deterministic(self):
        """Same input -> same output, every time — no AI, no randomness."""

        make_purchase_ticket_task()

        first = get_task_descriptor("purchase_ticket")
        second = get_task_descriptor("purchase_ticket")

        self.assertEqual(first, second)

    def test_descriptor_never_mentions_barriers_or_accessibility_judgements(self):
        """Phase 3 describes facts, never accessibility conclusions —
        this is the architectural boundary Phase 4 depends on."""

        make_purchase_ticket_task()
        descriptor = get_task_descriptor("purchase_ticket")

        serialized = str(descriptor).lower()
        for forbidden in ("barrier", "too small", "cannot use", "accessible", "inaccessible"):
            self.assertNotIn(forbidden, serialized)


class TaskAnalyzeAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        make_purchase_ticket_task()

    def test_analyze_known_task_returns_200(self):
        response = self.client.post("/api/tasks/analyze/", {"task_id": "purchase_ticket"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["task_id"], "purchase_ticket")
        self.assertEqual(len(response.data["steps"]), 3)

    def test_analyze_unknown_task_returns_404(self):
        response = self.client.post("/api/tasks/analyze/", {"task_id": "does_not_exist"}, format="json")
        self.assertEqual(response.status_code, 404)

    def test_analyze_missing_task_id_returns_400(self):
        response = self.client.post("/api/tasks/analyze/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_error_response_does_not_leak_stack_trace(self):
        response = self.client.post("/api/tasks/analyze/", {"task_id": "does_not_exist"}, format="json")
        self.assertNotIn("Traceback", str(response.data))
