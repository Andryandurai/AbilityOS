from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from abilities.services.profile_service import get_or_create_profile
from questionnaire.models import QuestionnaireQuestion, QuestionnaireResponse, QuestionnaireSession
from questionnaire.services import questionnaire_service as svc
from users.models import User
from users.services import consent_service


def make_user(username, granted=True):
    user = User.objects.create_user(username=username, password="x")
    if granted:
        consent_service.grant_consent(user)
    return user


# --------------------------------------------------------------------------
# Questionnaire retrieval
# --------------------------------------------------------------------------
class QuestionnaireRetrievalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_questionnaire")

    def setUp(self):
        self.client = APIClient()

    def test_current_questionnaire_can_be_retrieved(self):
        response = self.client.get("/api/questionnaire/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["questions"]), 10)

    def test_question_order_is_correct(self):
        response = self.client.get("/api/questionnaire/")
        orders = [q["order"] for q in response.data["questions"]]
        self.assertEqual(orders, sorted(orders))
        self.assertEqual(response.data["questions"][0]["key"], "vision")

    def test_question_version_is_returned(self):
        response = self.client.get("/api/questionnaire/")
        self.assertEqual(response.data["version"], 1)

    def test_options_are_valid_against_allowed_levels(self):
        from abilities.constants import ALLOWED_LEVELS

        response = self.client.get("/api/questionnaire/")
        for question in response.data["questions"]:
            values = [opt["value"] for opt in question["options"]]
            self.assertEqual(set(values), set(ALLOWED_LEVELS[question["key"]]))

    def test_retrieval_requires_no_authentication(self):
        response = self.client.get("/api/questionnaire/")
        self.assertEqual(response.status_code, 200)


# --------------------------------------------------------------------------
# Questionnaire start
# --------------------------------------------------------------------------
class QuestionnaireStartTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_questionnaire")

    def setUp(self):
        self.client = APIClient()
        self.user = make_user("starter")

    def test_authenticated_consented_user_can_start(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/questionnaire/start/", {}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIn("session_id", response.data)

    def test_unauthenticated_user_cannot_start(self):
        response = self.client.post("/api/questionnaire/start/", {}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_session_belongs_to_authenticated_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/questionnaire/start/", {}, format="json")
        session = QuestionnaireSession.objects.get(pk=response.data["session_id"])
        self.assertEqual(session.user_id, self.user.id)

    def test_session_version_is_stored(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/questionnaire/start/", {}, format="json")
        self.assertEqual(response.data["version"], 1)

    def test_start_without_consent_rejected(self):
        unconsented = make_user("no_consent", granted=False)
        self.client.force_authenticate(user=unconsented)
        response = self.client.post("/api/questionnaire/start/", {}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(QuestionnaireSession.objects.filter(user=unconsented).exists())


# --------------------------------------------------------------------------
# Response
# --------------------------------------------------------------------------
class QuestionnaireResponseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_questionnaire")

    def setUp(self):
        self.client = APIClient()
        self.user = make_user("responder")
        self.other = make_user("other_responder")
        self.client.force_authenticate(user=self.user)
        self.session_id = self.client.post("/api/questionnaire/start/", {}, format="json").data["session_id"]
        self.vision_question = QuestionnaireQuestion.objects.get(key="vision", version=1)

    def test_user_can_answer_own_question(self):
        response = self.client.post(
            f"/api/questionnaire/{self.session_id}/response/",
            {"question_id": self.vision_question.id, "selected_value": "typical"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(QuestionnaireResponse.objects.filter(session_id=self.session_id).exists())

    def test_user_cannot_answer_another_users_session(self):
        self.client.force_authenticate(user=self.other)
        response = self.client.post(
            f"/api/questionnaire/{self.session_id}/response/",
            {"question_id": self.vision_question.id, "selected_value": "typical"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_invalid_question_rejected(self):
        response = self.client.post(
            f"/api/questionnaire/{self.session_id}/response/",
            {"question_id": 999999, "selected_value": "typical"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_invalid_selected_value_rejected(self):
        response = self.client.post(
            f"/api/questionnaire/{self.session_id}/response/",
            {"question_id": self.vision_question.id, "selected_value": "made-up-value"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_duplicate_response_updates_rather_than_duplicates(self):
        self.client.post(
            f"/api/questionnaire/{self.session_id}/response/",
            {"question_id": self.vision_question.id, "selected_value": "typical"},
            format="json",
        )
        self.client.post(
            f"/api/questionnaire/{self.session_id}/response/",
            {"question_id": self.vision_question.id, "selected_value": "large-text-needed"},
            format="json",
        )
        responses = QuestionnaireResponse.objects.filter(session_id=self.session_id, question=self.vision_question)
        self.assertEqual(responses.count(), 1)
        self.assertEqual(responses.first().selected_value, "large-text-needed")

    def test_missing_required_data_rejected(self):
        response = self.client.post(f"/api/questionnaire/{self.session_id}/response/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_cannot_answer_after_completion(self):
        for question in QuestionnaireQuestion.objects.filter(version=1):
            self.client.post(
                f"/api/questionnaire/{self.session_id}/response/",
                {"question_id": question.id, "selected_value": question.options[0]["value"]},
                format="json",
            )
        self.client.post(f"/api/questionnaire/{self.session_id}/complete/", {}, format="json")

        response = self.client.post(
            f"/api/questionnaire/{self.session_id}/response/",
            {"question_id": self.vision_question.id, "selected_value": "typical"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)


# --------------------------------------------------------------------------
# Completion
# --------------------------------------------------------------------------
class QuestionnaireCompletionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_questionnaire")

    def setUp(self):
        self.client = APIClient()
        self.user = make_user("completer")
        self.client.force_authenticate(user=self.user)
        self.session_id = self.client.post("/api/questionnaire/start/", {}, format="json").data["session_id"]

    def _answer_all(self, overrides=None):
        overrides = overrides or {}
        for question in QuestionnaireQuestion.objects.filter(version=1):
            value = overrides.get(question.key, question.options[0]["value"])
            self.client.post(
                f"/api/questionnaire/{self.session_id}/response/",
                {"question_id": question.id, "selected_value": value},
                format="json",
            )

    def test_incomplete_questionnaire_cannot_complete(self):
        response = self.client.post(f"/api/questionnaire/{self.session_id}/complete/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_complete_questionnaire_generates_dimensions(self):
        self._answer_all({"vision": "large-text-needed"})
        response = self.client.post(f"/api/questionnaire/{self.session_id}/complete/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["dimensions"]["vision"]["level"], "large-text-needed")

    def test_generated_dimensions_use_existing_dimension_keys(self):
        from abilities.constants import DIMENSION_KEYS

        self._answer_all()
        response = self.client.post(f"/api/questionnaire/{self.session_id}/complete/", {}, format="json")
        self.assertEqual(set(response.data["dimensions"].keys()), set(DIMENSION_KEYS))

    def test_generated_values_use_existing_allowed_levels(self):
        from abilities.constants import ALLOWED_LEVELS

        self._answer_all()
        response = self.client.post(f"/api/questionnaire/{self.session_id}/complete/", {}, format="json")
        for key, payload in response.data["dimensions"].items():
            self.assertIn(payload["level"], ALLOWED_LEVELS[key])

    def test_completing_twice_is_idempotent(self):
        self._answer_all()
        first = self.client.post(f"/api/questionnaire/{self.session_id}/complete/", {}, format="json")
        second = self.client.post(f"/api/questionnaire/{self.session_id}/complete/", {}, format="json")
        self.assertEqual(first.data["dimensions"], second.data["dimensions"])

    def test_tampered_question_id_cannot_inject_arbitrary_dimension(self):
        """Section 20's negative test: posting a question_id that doesn't
        belong to the seeded questionnaire must never end up influencing
        the generated dimensions."""
        response = self.client.post(
            f"/api/questionnaire/{self.session_id}/response/",
            {"question_id": 987654, "selected_value": "typical"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(QuestionnaireResponse.objects.filter(session_id=self.session_id).count(), 0)


# --------------------------------------------------------------------------
# Profile integration -- the confirm step, and the service layer directly
# --------------------------------------------------------------------------
class ProfileIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_questionnaire")

    def setUp(self):
        self.client = APIClient()
        self.user = make_user("confirmer")
        self.client.force_authenticate(user=self.user)
        self.session_id = self.client.post("/api/questionnaire/start/", {}, format="json").data["session_id"]
        for question in QuestionnaireQuestion.objects.filter(version=1):
            value = "large-text-needed" if question.key == "vision" else question.options[0]["value"]
            self.client.post(
                f"/api/questionnaire/{self.session_id}/response/",
                {"question_id": question.id, "selected_value": value},
                format="json",
            )

    def test_cannot_confirm_before_completing(self):
        response = self.client.post(f"/api/questionnaire/{self.session_id}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_confirmed_profile_uses_manual_source(self):
        self.client.post(f"/api/questionnaire/{self.session_id}/complete/", {}, format="json")
        response = self.client.post(f"/api/questionnaire/{self.session_id}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["dimensions"]["vision"]["source"], "manual")

    def test_profile_not_saved_before_confirmation(self):
        """Section 14's core requirement: completing (previewing) must
        never itself write to AbilityProfile."""
        self.client.post(f"/api/questionnaire/{self.session_id}/complete/", {}, format="json")
        profile = get_or_create_profile(self.user)
        self.assertNotEqual(profile.dimensions.get("vision", {}).get("level"), "large-text-needed")

    def test_confirmed_profile_is_saved_and_retrievable_via_existing_endpoint(self):
        self.client.post(f"/api/questionnaire/{self.session_id}/complete/", {}, format="json")
        self.client.post(f"/api/questionnaire/{self.session_id}/confirm/", {}, format="json")

        response = self.client.get(f"/api/users/{self.user.id}/ability-profile/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["dimensions"]["vision"]["level"], "large-text-needed")

    def test_abandoning_after_preview_leaves_profile_unchanged(self):
        """Section 14's core scenario: the user reaches the generated-
        profile preview (complete/) but never confirms it -- the real
        AbilityProfile must be completely untouched, not partially
        written."""
        profile_before = get_or_create_profile(self.user).dimensions

        self.client.post(f"/api/questionnaire/{self.session_id}/complete/", {}, format="json")

        profile_after = get_or_create_profile(self.user).dimensions
        self.assertEqual(profile_before, profile_after)
        self.assertNotEqual(profile_after.get("vision", {}).get("level"), "large-text-needed")

    def test_write_path_is_apply_manual_update_not_direct_orm(self):
        """Confirms the architectural rule (section 3/33) at the service
        level: confirm_questionnaire() produces a profile whose dimensions
        carry the exact confidence/source apply_manual_update() always
        sets (0.95/manual) -- a direct ORM write from questionnaire code
        would have no reason to reproduce that default."""
        session = QuestionnaireSession.objects.get(pk=self.session_id)
        svc.complete_questionnaire(session)
        profile = svc.confirm_questionnaire(session)
        self.assertEqual(profile.dimensions["vision"]["confidence"], 0.95)
        self.assertEqual(profile.dimensions["vision"]["source"], "manual")

    def test_existing_manual_editor_write_path_still_works_after_confirm(self):
        """Section 23: questionnaire and manual editor must both converge
        on apply_manual_update() without interfering with each other."""
        self.client.post(f"/api/questionnaire/{self.session_id}/complete/", {}, format="json")
        self.client.post(f"/api/questionnaire/{self.session_id}/confirm/", {}, format="json")

        response = self.client.patch(
            f"/api/users/{self.user.id}/ability-profile/",
            {"dimensions": {"vision": {"level": "typical"}}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["dimensions"]["vision"]["level"], "typical")


# --------------------------------------------------------------------------
# Consent
# --------------------------------------------------------------------------
class QuestionnaireConsentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_questionnaire")

    def setUp(self):
        self.client = APIClient()

    def test_questionnaire_cannot_proceed_without_consent(self):
        user = make_user("unconsented_person", granted=False)
        self.client.force_authenticate(user=user)
        response = self.client.post("/api/questionnaire/start/", {}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_consent_remains_linked_to_correct_user(self):
        user = make_user("consented_person")
        self.client.force_authenticate(user=user)
        response = self.client.get(f"/api/users/{user.id}/consent/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"], user.id)
        self.assertTrue(response.data["granted"])

    def test_user_cannot_modify_another_users_consent(self):
        owner = make_user("consent_owner")
        attacker = make_user("consent_attacker")
        self.client.force_authenticate(user=attacker)
        response = self.client.post(f"/api/users/{owner.id}/consent/", {"granted": False}, format="json")
        self.assertEqual(response.status_code, 403)


# --------------------------------------------------------------------------
# Security -- User A vs. User B, end to end through the real API
# --------------------------------------------------------------------------
class QuestionnaireSecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_questionnaire")

    def setUp(self):
        self.client = APIClient()
        self.user_a = make_user("security_user_a")
        self.user_b = make_user("security_user_b")

        self.client.force_authenticate(user=self.user_a)
        self.session_id = self.client.post("/api/questionnaire/start/", {}, format="json").data["session_id"]
        self.question = QuestionnaireQuestion.objects.filter(version=1).first()
        self.client.post(
            f"/api/questionnaire/{self.session_id}/response/",
            {"question_id": self.question.id, "selected_value": self.question.options[0]["value"]},
            format="json",
        )

    def test_user_b_cannot_view_or_touch_user_as_session(self):
        self.client.force_authenticate(user=self.user_b)
        self.assertEqual(
            self.client.post(
                f"/api/questionnaire/{self.session_id}/response/",
                {"question_id": self.question.id, "selected_value": self.question.options[0]["value"]},
                format="json",
            ).status_code,
            403,
        )

    def test_user_b_cannot_modify_user_as_responses(self):
        self.client.force_authenticate(user=self.user_b)
        self.client.post(
            f"/api/questionnaire/{self.session_id}/response/",
            {"question_id": self.question.id, "selected_value": self.question.options[-1]["value"]},
            format="json",
        )
        stored = QuestionnaireResponse.objects.get(session_id=self.session_id, question=self.question)
        self.assertEqual(stored.selected_value, self.question.options[0]["value"])

    def test_user_b_cannot_complete_user_as_questionnaire(self):
        self.client.force_authenticate(user=self.user_b)
        response = self.client.post(f"/api/questionnaire/{self.session_id}/complete/", {}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_user_b_cannot_confirm_user_as_questionnaire(self):
        self.client.force_authenticate(user=self.user_b)
        response = self.client.post(f"/api/questionnaire/{self.session_id}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, 403)


# --------------------------------------------------------------------------
# Service-level unit tests
# --------------------------------------------------------------------------
class QuestionnaireServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_questionnaire")

    def test_current_version_defaults_to_one(self):
        self.assertEqual(svc.current_version(), 1)

    def test_start_questionnaire_creates_session_at_current_version(self):
        user = make_user("service_user")
        session = svc.start_questionnaire(user)
        self.assertEqual(session.version, 1)
        self.assertEqual(session.user_id, user.id)
        self.assertFalse(session.is_completed)

    def test_save_response_rejects_unknown_dimension_key(self):
        """Defense in depth: even if a QuestionnaireQuestion row somehow
        carried a key outside DIMENSION_KEYS, save_response must still
        refuse it."""
        user = make_user("bad_key_user")
        session = svc.start_questionnaire(user)
        rogue_question = QuestionnaireQuestion.objects.create(
            key="not_a_real_dimension", version=1, question_text="?", order=99, options=[{"value": "x", "label": "x"}]
        )
        with self.assertRaises(svc.QuestionnaireError):
            svc.save_response(session, rogue_question.id, "x")
