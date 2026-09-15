from django.test import TestCase
from rest_framework.test import APIClient

from users.models import ConsentRecord, User
from users.services import consent_service


class ConsentServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="grace", password="x")

    def test_get_or_create_starts_ungranted(self):
        record = consent_service.get_or_create_consent(self.user)
        self.assertFalse(record.granted)
        self.assertEqual(record.scope, [])

    def test_grant_consent_sets_scope_and_timestamp(self):
        record = consent_service.grant_consent(self.user)
        self.assertTrue(record.granted)
        self.assertIn(ConsentRecord.SCOPE_INTERACTION_ADAPTATION, record.scope)
        self.assertIsNotNone(record.granted_at)

    def test_revoke_consent_clears_timestamp(self):
        consent_service.grant_consent(self.user)
        record = consent_service.revoke_consent(self.user)
        self.assertFalse(record.granted)
        self.assertIsNone(record.granted_at)

    def test_is_consented_for_adaptation_requires_correct_scope(self):
        self.assertFalse(consent_service.is_consented_for_adaptation(self.user))

        consent_service.grant_consent(self.user, scope=["behavioural_inference"])
        self.assertFalse(consent_service.is_consented_for_adaptation(self.user))

        consent_service.grant_consent(self.user, scope=["interaction_adaptation"])
        self.assertTrue(consent_service.is_consented_for_adaptation(self.user))


class ConsentAPIAuthorizationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username="hank", password="x")
        self.attacker = User.objects.create_user(username="ivan", password="x")

    def test_authenticated_user_cannot_change_another_users_consent(self):
        self.client.force_authenticate(user=self.attacker)
        response = self.client.post(f"/api/users/{self.owner.id}/consent/", {"granted": True}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_authenticated_user_can_change_own_consent(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(f"/api/users/{self.owner.id}/consent/", {"granted": True}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["granted"])

    def test_anonymous_demo_request_can_still_grant_consent(self):
        response = self.client.post(f"/api/users/{self.owner.id}/consent/", {"granted": True}, format="json")
        self.assertEqual(response.status_code, 200)
