from django.test import TestCase
from rest_framework.test import APIClient

from abilities.constants import DEFAULT_LEVEL
from abilities.models import AbilityProfile, DIMENSION_KEYS
from users.models import User


class AbilityProfileModelTests(TestCase):
    def test_creation_uses_each_dimensions_own_baseline_default(self):
        """Not every dimension's controlled vocabulary includes "typical"
        (reach's baseline is "full", fatigue's is "fresh") — a fresh
        profile must use each dimension's own no-barrier default, not a
        single hardcoded string."""

        user = User.objects.create_user(username="alice", password="x")
        profile = AbilityProfile.objects.create(user=user)

        for key in DIMENSION_KEYS:
            self.assertIn(key, profile.dimensions)
            self.assertEqual(profile.dimensions[key]["level"], DEFAULT_LEVEL[key])
            self.assertEqual(profile.dimensions[key]["source"], "default")

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

    def test_patch_rejects_invalid_ability_value(self):
        response = self.client.patch(
            f"/api/users/{self.user.id}/ability-profile/",
            data={"dimensions": {"vision": {"level": "x-ray-vision"}}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_rejects_confidence_above_one(self):
        response = self.client.patch(
            f"/api/users/{self.user.id}/ability-profile/",
            data={"dimensions": {"vision": {"level": "typical", "confidence": 1.5}}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_rejects_confidence_below_zero(self):
        response = self.client.patch(
            f"/api/users/{self.user.id}/ability-profile/",
            data={"dimensions": {"vision": {"level": "typical", "confidence": -0.1}}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_rejects_invalid_source(self):
        response = self.client.patch(
            f"/api/users/{self.user.id}/ability-profile/",
            data={"dimensions": {"vision": {"level": "typical", "source": "guessed"}}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_rejects_invalid_modality(self):
        response = self.client.patch(
            f"/api/users/{self.user.id}/ability-profile/",
            data={"preferred_modality": "telepathic"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_patch_rejects_unknown_dimension(self):
        response = self.client.patch(
            f"/api/users/{self.user.id}/ability-profile/",
            data={"dimensions": {"telepathy": {"level": "typical"}}},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_delete_clears_profile_to_defaults(self):
        self.client.patch(
            f"/api/users/{self.user.id}/ability-profile/",
            data={"dimensions": {"dexterity": {"level": "single-tap-only"}}},
            format="json",
        )
        response = self.client.delete(f"/api/users/{self.user.id}/ability-profile/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["dimensions"]["dexterity"]["level"], "typical")
        self.assertEqual(response.data["dimensions"]["dexterity"]["source"], "default")

    def test_authenticated_user_cannot_edit_another_users_profile(self):
        owner = User.objects.create_user(username="owner", password="x")
        attacker = User.objects.create_user(username="attacker", password="x")
        self.client.force_authenticate(user=attacker)

        response = self.client.patch(
            f"/api/users/{owner.id}/ability-profile/",
            data={"dimensions": {"vision": {"level": "large-text-needed"}}},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_authenticated_user_can_edit_own_profile(self):
        owner = User.objects.create_user(username="owner2", password="x")
        self.client.force_authenticate(user=owner)

        response = self.client.patch(
            f"/api/users/{owner.id}/ability-profile/",
            data={"dimensions": {"vision": {"level": "large-text-needed"}}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

    def test_anonymous_demo_request_is_still_permitted(self):
        """The login-free hackathon demo path (Phase 1 architecture) must
        keep working — ownership is only enforced for authenticated
        requests, per Phase 2 section 23's explicit carve-out."""

        response = self.client.patch(
            f"/api/users/{self.user.id}/ability-profile/",
            data={"dimensions": {"vision": {"level": "large-text-needed"}}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)


class ProfileServiceTests(TestCase):
    """Direct tests of abilities.services.profile_service — the "manual
    beats inferred beats default" rule (Phase 2 section 7) is not exercised
    by any live endpoint yet (no inference pipeline exists), so it's tested
    at the service layer directly."""

    def setUp(self):
        self.user = User.objects.create_user(username="frank", password="x")
        self.profile = AbilityProfile.objects.create(user=self.user)

    def test_manual_update_always_overwrites(self):
        from abilities.services.profile_service import apply_manual_update

        apply_manual_update(self.profile, dimensions={"dexterity": {"level": "reduced-precision"}})
        self.assertEqual(self.profile.dimensions["dexterity"]["source"], "manual")

    def test_inferred_update_does_not_overwrite_existing_manual_value(self):
        from abilities.services.profile_service import apply_inferred_update, apply_manual_update

        apply_manual_update(self.profile, dimensions={"dexterity": {"level": "reduced-precision", "confidence": 0.9}})
        apply_inferred_update(self.profile, "dexterity", "typical", 0.99, source="inferred")

        self.assertEqual(self.profile.dimensions["dexterity"]["level"], "reduced-precision")
        self.assertEqual(self.profile.dimensions["dexterity"]["source"], "manual")

    def test_inferred_update_does_overwrite_a_default_value(self):
        from abilities.services.profile_service import apply_inferred_update

        apply_inferred_update(self.profile, "dexterity", "reduced-precision", 0.7, source="inferred")

        self.assertEqual(self.profile.dimensions["dexterity"]["level"], "reduced-precision")
        self.assertEqual(self.profile.dimensions["dexterity"]["source"], "inferred")

    def test_invalid_level_raises_profile_validation_error(self):
        from abilities.services.profile_service import ProfileValidationError, apply_manual_update

        with self.assertRaises(ProfileValidationError):
            apply_manual_update(self.profile, dimensions={"vision": {"level": "not-a-real-level"}})

    def test_clear_profile_resets_everything(self):
        from abilities.services.profile_service import apply_manual_update, clear_profile

        apply_manual_update(
            self.profile,
            dimensions={"dexterity": {"level": "single-tap-only"}},
            preferred_modality="voice",
            preferences={"text_scale": 1.5},
        )
        clear_profile(self.profile)

        self.assertEqual(self.profile.dimensions["dexterity"]["level"], "typical")
        self.assertEqual(self.profile.preferred_modality, AbilityProfile.MODALITY_VISUAL)
        self.assertEqual(self.profile.preferences, {})
