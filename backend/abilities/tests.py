from django.test import TestCase
from rest_framework.test import APIClient

from abilities.models import AbilityProfile, DIMENSION_KEYS
from users.models import User


class AbilityProfileModelTests(TestCase):
    def test_creation_uses_typical_defaults(self):
        user = User.objects.create_user(username="alice", password="x")
        profile = AbilityProfile.objects.create(user=user)

        for key in DIMENSION_KEYS:
            self.assertIn(key, profile.dimensions)
            self.assertEqual(profile.dimensions[key]["level"], "typical")

    def test_set_dimension_overwrites_level_and_source(self):
        user = User.objects.create_user(username="bob", password="x")
        profile = AbilityProfile.objects.create(user=user)

        profile.set_dimension("dexterity", "reduced-precision", confidence=0.8, source="manual")

        self.assertEqual(profile.dimensions["dexterity"]["level"], "reduced-precision")
        self.assertEqual(profile.dimensions["dexterity"]["source"], "manual")

    def test_set_dimension_rejects_unknown_key(self):
        user = User.objects.create_user(username="carol", password="x")
        profile = AbilityProfile.objects.create(user=user)

        with self.assertRaises(ValueError):
            profile.set_dimension("telepathy", "typical")

    def test_update_dimension_confidence_is_clamped(self):
        user = User.objects.create_user(username="dora", password="x")
        profile = AbilityProfile.objects.create(user=user)
        profile.set_dimension("vision", "typical", confidence=0.95)

        profile.update_dimension_confidence("vision", 0.5)
        self.assertEqual(profile.dimensions["vision"]["confidence"], 1.0)

        profile.update_dimension_confidence("vision", -5)
        self.assertEqual(profile.dimensions["vision"]["confidence"], 0.0)


class AbilityProfileAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="erin", password="x")

    def test_get_creates_profile_if_missing(self):
        response = self.client.get(f"/api/users/{self.user.id}/ability-profile/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("dimensions", response.data)

    def test_patch_updates_dimension_and_tags_manual_source(self):
        response = self.client.patch(
            f"/api/users/{self.user.id}/ability-profile/",
            data={"dimensions": {"dexterity": {"level": "single-tap-only"}}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["dimensions"]["dexterity"]["level"], "single-tap-only")
        self.assertEqual(response.data["dimensions"]["dexterity"]["source"], "manual")

    def test_patch_updates_preferred_modality(self):
        response = self.client.patch(
            f"/api/users/{self.user.id}/ability-profile/",
            data={"preferred_modality": AbilityProfile.MODALITY_VOICE},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["preferred_modality"], "voice")
