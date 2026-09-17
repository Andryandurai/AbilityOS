from django.test import TestCase
from rest_framework.test import APIClient

from abilities.models import AbilityProfile
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

    def test_authenticated_user_cannot_read_another_users_consent(self):
        """Phase 1 section 11: GET previously had no ownership check."""
        self.client.force_authenticate(user=self.attacker)
        response = self.client.get(f"/api/users/{self.owner.id}/consent/")
        self.assertEqual(response.status_code, 403)

    def test_authenticated_user_can_read_own_consent(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(f"/api/users/{self.owner.id}/consent/")
        self.assertEqual(response.status_code, 200)

    def test_anonymous_demo_request_can_still_read_consent(self):
        response = self.client.get(f"/api/users/{self.owner.id}/consent/")
        self.assertEqual(response.status_code, 200)


# ---------------------------------------------------------------------------
# Phase 1: Real User Authentication (register / login / me / logout)
# ---------------------------------------------------------------------------
class RegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _register(self, **overrides):
        payload = {
            "username": "newperson",
            "email": "newperson@example.com",
            "display_name": "New Person",
            "password": "a-strong-unusual-passphrase-93",
            "password_confirm": "a-strong-unusual-passphrase-93",
        }
        payload.update(overrides)
        return self.client.post("/api/auth/register/", payload, format="json")

    def test_successful_registration(self):
        response = self._register()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["username"], "newperson")
        self.assertTrue(User.objects.filter(username="newperson").exists())

    def test_password_is_hashed_not_stored_in_plaintext(self):
        self._register()
        user = User.objects.get(username="newperson")
        self.assertNotEqual(user.password, "a-strong-unusual-passphrase-93")
        self.assertTrue(user.password.startswith("pbkdf2_") or "$" in user.password)
        self.assertTrue(user.check_password("a-strong-unusual-passphrase-93"))

    def test_new_account_is_not_a_demo_profile(self):
        self._register()
        user = User.objects.get(username="newperson")
        self.assertFalse(user.is_demo_profile)

    def test_duplicate_username_rejected(self):
        self._register()
        response = self._register(email="different@example.com")
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.data)

    def test_duplicate_email_rejected(self):
        self._register()
        response = self._register(username="someoneelse")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)

    def test_mismatched_password_confirmation_rejected(self):
        response = self._register(password_confirm="something-else-entirely")
        self.assertEqual(response.status_code, 400)

    def test_weak_password_rejected(self):
        response = self._register(username="weakpass", email="weak@example.com", password="12345678", password_confirm="12345678")
        self.assertEqual(response.status_code, 400)

    def test_registration_does_not_eagerly_create_ability_profile(self):
        """Phase 1 section 5: no AbilityProfile until the normal lazy
        get_or_create_profile() path (AbilityProfileView) is ever hit."""
        self._register()
        user = User.objects.get(username="newperson")
        self.assertFalse(AbilityProfile.objects.filter(user=user).exists())


class LoginTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="loginuser", password="correct-horse-battery-staple")

    def test_valid_credentials_return_access_and_refresh_tokens(self):
        response = self.client.post(
            "/api/auth/login/", {"username": "loginuser", "password": "correct-horse-battery-staple"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["username"], "loginuser")

    def test_invalid_password_rejected(self):
        response = self.client.post(
            "/api/auth/login/", {"username": "loginuser", "password": "wrong-password"}, format="json"
        )
        self.assertEqual(response.status_code, 401)

    def test_unknown_user_rejected(self):
        response = self.client.post(
            "/api/auth/login/", {"username": "does-not-exist", "password": "whatever"}, format="json"
        )
        self.assertEqual(response.status_code, 401)


class MeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="meuser", password="x", email="me@example.com", display_name="Me User"
        )

    def test_unauthenticated_me_rejected(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_me_returns_current_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], self.user.id)
        self.assertEqual(response.data["username"], "meuser")
        self.assertEqual(response.data["email"], "me@example.com")
        self.assertFalse(response.data["is_demo_profile"])

    def test_me_never_exposes_password_or_tokens(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/auth/me/")
        payload = str(response.data)
        self.assertNotIn("password", payload)
        self.assertNotIn(self.user.password, payload)

    def test_me_ignores_a_spoofed_user_id_and_uses_request_user(self):
        """Section 7: /me must derive identity from request.user, never
        from a client-supplied id."""
        other = User.objects.create_user(username="otherperson", password="x")
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/auth/me/", {"user_id": other.id})
        self.assertEqual(response.data["id"], self.user.id)


class LogoutTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="logoutuser", password="correct-horse-battery-staple")

    def _login(self):
        return self.client.post(
            "/api/auth/login/", {"username": "logoutuser", "password": "correct-horse-battery-staple"}, format="json"
        ).data

    def test_unauthenticated_logout_rejected(self):
        response = self.client.post("/api/auth/logout/", {"refresh": "irrelevant"}, format="json")
        self.assertEqual(response.status_code, 401)

    def test_authenticated_logout_blacklists_refresh_token(self):
        tokens = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = self.client.post("/api/auth/logout/", {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(response.status_code, 204)

    def test_reusing_a_blacklisted_refresh_token_fails(self):
        """Section 8/16: verifies the blacklist actually took effect,
        rather than asserting logout succeeded and stopping there."""
        tokens = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.client.post("/api/auth/logout/", {"refresh": tokens["refresh"]}, format="json")

        second_attempt = self.client.post("/api/auth/logout/", {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(second_attempt.status_code, 400)

    def test_logout_requires_a_refresh_token_in_the_body(self):
        tokens = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        response = self.client.post("/api/auth/logout/", {}, format="json")
        self.assertEqual(response.status_code, 400)


class AbilityProfileOwnershipTests(TestCase):
    """Phase 1 section 11 — the AbilityProfileView.get() gap the Phase 0
    audit found."""

    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username="profileowner", password="x")
        self.attacker = User.objects.create_user(username="profileattacker", password="x")

    def test_authenticated_user_cannot_read_another_users_ability_profile(self):
        self.client.force_authenticate(user=self.attacker)
        response = self.client.get(f"/api/users/{self.owner.id}/ability-profile/")
        self.assertEqual(response.status_code, 403)

    def test_authenticated_user_can_read_own_ability_profile(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(f"/api/users/{self.owner.id}/ability-profile/")
        self.assertEqual(response.status_code, 200)

    def test_anonymous_demo_request_can_still_read_any_ability_profile(self):
        """The anonymous demo path (SelectUserPage) must be completely
        unaffected: assert_owner() is a no-op when unauthenticated."""
        response = self.client.get(f"/api/users/{self.owner.id}/ability-profile/")
        self.assertEqual(response.status_code, 200)
