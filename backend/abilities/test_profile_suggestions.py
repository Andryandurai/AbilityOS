"""Phase 3 (Profile Suggestions & User Profile Selection) tests.

Kept separate from abilities/tests.py, mirroring the existing
barriers/test_rules.py pattern in this codebase of giving a substantial
new feature its own test file rather than growing one file indefinitely.
"""

from django.test import TestCase
from rest_framework.test import APIClient

from abilities.constants import ALLOWED_LEVELS, DIMENSION_KEYS
from abilities.models import AbilityProfile, UserProfileSelection
from abilities.profiles import CANONICAL_PROFILES
from abilities.services.profile_service import get_or_create_profile
from abilities.services.selection_service import delete_selection, list_selections, upsert_selection
from abilities.services.suggestion_service import list_all_profiles, suggest_profiles
from users.models import User


def dims(**kwargs):
    return {k: {"level": v, "confidence": 0.8, "source": "manual"} for k, v in kwargs.items()}


# --------------------------------------------------------------------------
# Canonical data integrity -- every trigger dimension must be real
# --------------------------------------------------------------------------
class CanonicalProfileDataTests(TestCase):
    def test_every_profile_has_nine_entries(self):
        self.assertEqual(len(CANONICAL_PROFILES), 9)

    def test_every_trigger_dimension_key_is_a_real_dimension(self):
        for profile in CANONICAL_PROFILES:
            for dim_key in profile["dimensions"]:
                self.assertIn(dim_key, DIMENSION_KEYS, f"{profile['key']} uses unknown dimension '{dim_key}'")

    def test_every_trigger_value_is_allowed_for_its_dimension(self):
        for profile in CANONICAL_PROFILES:
            for dim_key, value in profile["dimensions"].items():
                self.assertIn(
                    value,
                    ALLOWED_LEVELS[dim_key],
                    f"{profile['key']}.{dim_key}='{value}' is not in ALLOWED_LEVELS",
                )

    def test_profile_keys_are_unique(self):
        keys = [p["key"] for p in CANONICAL_PROFILES]
        self.assertEqual(len(keys), len(set(keys)))


# --------------------------------------------------------------------------
# Suggestion matching logic (section 25's 9 mandated scenarios)
# --------------------------------------------------------------------------
class SuggestionMatchingTests(TestCase):
    def test_low_vision_reduced_dexterity(self):
        result = suggest_profiles(dims(vision="large-text-needed", dexterity="reduced-precision"))
        keys = [s["profile_key"] for s in result]
        self.assertIn("low_vision_reduced_dexterity", keys)

    def test_hearing_relies_on_visual(self):
        result = suggest_profiles(dims(hearing="relies-on-visual"))
        keys = [s["profile_key"] for s in result]
        self.assertIn("hearing_difficulty", keys)

    def test_cognition_needs_step_by_step(self):
        result = suggest_profiles(dims(cognition="needs-step-by-step"))
        keys = [s["profile_key"] for s in result]
        self.assertIn("cognitive_load", keys)

    def test_limited_mobility_and_seated_reach(self):
        result = suggest_profiles(dims(reach="seated", mobility="limited"))
        keys = [s["profile_key"] for s in result]
        self.assertIn("limited_mobility_reach", keys)
        match = next(s for s in result if s["profile_key"] == "limited_mobility_reach")
        self.assertTrue(match["full_match"])
        self.assertEqual(sorted(match["matched_dimensions"]), ["mobility", "reach"])

    def test_speech_limited(self):
        result = suggest_profiles(dims(speech="limited"))
        keys = [s["profile_key"] for s in result]
        self.assertIn("speech_difficulty", keys)

    def test_fatigue_high(self):
        result = suggest_profiles(dims(fatigue="high"))
        keys = [s["profile_key"] for s in result]
        self.assertIn("fatigue_reduced_stamina", keys)

    def test_reaction_speed_slower(self):
        result = suggest_profiles(dims(reaction_speed="slower"))
        keys = [s["profile_key"] for s in result]
        self.assertIn("slower_reaction_speed", keys)

    def test_low_contrast_vision_and_relies_on_visual_hearing(self):
        result = suggest_profiles(dims(vision="low-contrast-sensitive", hearing="relies-on-visual"))
        keys = [s["profile_key"] for s in result]
        self.assertIn("visual_hearing_support", keys)
        match = next(s for s in result if s["profile_key"] == "visual_hearing_support")
        self.assertTrue(match["full_match"])
        self.assertEqual(match["match_count"], 2)

    def test_interaction_sensitivity_high(self):
        result = suggest_profiles(dims(interaction_sensitivity="high"))
        keys = [s["profile_key"] for s in result]
        self.assertIn("high_interaction_sensitivity", keys)

    def test_no_matching_profile_for_fully_typical_dimensions(self):
        result = suggest_profiles(get_or_create_profile(User.objects.create_user(username="typical_user", password="x")).dimensions)
        self.assertEqual(result, [])

    def test_multiple_matching_profiles_both_returned(self):
        """hearing=relies-on-visual alone genuinely matches two different
        canonical profiles (Hearing Difficulty fully, Visual + Hearing
        Support partially) -- both must be surfaced, not just one."""
        result = suggest_profiles(dims(hearing="relies-on-visual"))
        keys = {s["profile_key"] for s in result}
        self.assertEqual(keys, {"hearing_difficulty", "visual_hearing_support"})

    def test_partial_match_is_explainable_not_hidden(self):
        result = suggest_profiles(dims(vision="low-contrast-sensitive"))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["profile_key"], "visual_hearing_support")
        self.assertFalse(result[0]["full_match"])
        self.assertEqual(result[0]["matched_dimensions"], ["vision"])

    def test_suggestions_sorted_by_match_count_descending(self):
        result = suggest_profiles(dims(vision="low-contrast-sensitive", hearing="relies-on-visual"))
        counts = [s["match_count"] for s in result]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_list_all_profiles_always_returns_nine_regardless_of_dimensions(self):
        self.assertEqual(len(list_all_profiles()), 9)


# --------------------------------------------------------------------------
# API: suggestions endpoint
# --------------------------------------------------------------------------
class ProfileSuggestionsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="suggestee", password="x")

    def test_unauthenticated_cannot_view_suggestions(self):
        response = self.client.get(f"/api/users/{self.user.id}/profile-suggestions/")
        self.assertEqual(response.status_code, 401)

    def test_owner_can_view_own_suggestions(self):
        get_or_create_profile(self.user).set_dimension("speech", "limited")
        AbilityProfile.objects.get(user=self.user).save()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f"/api/users/{self.user.id}/profile-suggestions/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("suggestions", response.data)
        self.assertIn("all_profiles", response.data)
        self.assertEqual(len(response.data["all_profiles"]), 9)

    def test_another_user_cannot_view_suggestions(self):
        attacker = User.objects.create_user(username="suggestion_attacker", password="x")
        self.client.force_authenticate(user=attacker)
        response = self.client.get(f"/api/users/{self.user.id}/profile-suggestions/")
        self.assertEqual(response.status_code, 403)

    def test_viewing_suggestions_does_not_mutate_ability_profile(self):
        before = get_or_create_profile(self.user).dimensions
        self.client.force_authenticate(user=self.user)
        self.client.get(f"/api/users/{self.user.id}/profile-suggestions/")
        after = AbilityProfile.objects.get(user=self.user).dimensions
        self.assertEqual(before, after)

    def test_viewing_suggestions_does_not_create_selection_rows(self):
        self.client.force_authenticate(user=self.user)
        self.client.get(f"/api/users/{self.user.id}/profile-suggestions/")
        self.assertEqual(UserProfileSelection.objects.filter(user=self.user).count(), 0)


# --------------------------------------------------------------------------
# API: selections endpoint -- create/accept/reject/manually_added/validation
# --------------------------------------------------------------------------
class ProfileSelectionsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="selector", password="x")
        self.client.force_authenticate(user=self.user)

    def _select(self, profile_key, status):
        return self.client.post(
            f"/api/users/{self.user.id}/profile-selections/",
            {"profile_key": profile_key, "status": status},
            format="json",
        )

    def test_accept_a_suggested_profile(self):
        response = self._select("hearing_difficulty", "accepted")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "accepted")

    def test_reject_a_suggested_profile(self):
        response = self._select("hearing_difficulty", "rejected")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "rejected")

    def test_manually_add_a_profile_that_was_not_suggested(self):
        response = self._select("high_interaction_sensitivity", "manually_added")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "manually_added")

    def test_multiple_accepted_profiles_allowed(self):
        self._select("hearing_difficulty", "accepted")
        self._select("speech_difficulty", "accepted")
        selections = UserProfileSelection.objects.filter(user=self.user, status="accepted")
        self.assertEqual(selections.count(), 2)

    def test_duplicate_selection_updates_rather_than_duplicates(self):
        self._select("hearing_difficulty", "accepted")
        self._select("hearing_difficulty", "rejected")
        rows = UserProfileSelection.objects.filter(user=self.user, profile_key="hearing_difficulty")
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().status, "rejected")

    def test_invalid_profile_key_rejected(self):
        response = self._select("not_a_real_profile", "accepted")
        self.assertEqual(response.status_code, 400)

    def test_invalid_status_rejected(self):
        response = self._select("hearing_difficulty", "not_a_real_status")
        self.assertEqual(response.status_code, 400)

    def test_selection_does_not_modify_ability_profile(self):
        before = get_or_create_profile(self.user).dimensions
        self._select("fatigue_reduced_stamina", "manually_added")
        after = AbilityProfile.objects.get(user=self.user).dimensions
        self.assertEqual(before, after)

    def test_get_selections_returns_created_rows(self):
        self._select("hearing_difficulty", "accepted")
        self._select("speech_difficulty", "rejected")
        response = self.client.get(f"/api/users/{self.user.id}/profile-selections/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_unauthenticated_cannot_create_selection(self):
        self.client.force_authenticate(user=None)
        response = self._select("hearing_difficulty", "accepted")
        self.assertEqual(response.status_code, 401)


# --------------------------------------------------------------------------
# Delete
# --------------------------------------------------------------------------
class ProfileSelectionDeleteAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="deleter", password="x")
        self.client.force_authenticate(user=self.user)
        self.client.post(
            f"/api/users/{self.user.id}/profile-selections/",
            {"profile_key": "hearing_difficulty", "status": "accepted"},
            format="json",
        )

    def test_owner_can_delete_own_selection(self):
        response = self.client.delete(f"/api/users/{self.user.id}/profile-selections/hearing_difficulty/")
        self.assertEqual(response.status_code, 204)
        self.assertFalse(UserProfileSelection.objects.filter(user=self.user, profile_key="hearing_difficulty").exists())

    def test_deleting_a_nonexistent_selection_returns_404(self):
        response = self.client.delete(f"/api/users/{self.user.id}/profile-selections/speech_difficulty/")
        self.assertEqual(response.status_code, 404)

    def test_rejecting_does_not_delete_the_row(self):
        """Section 20: rejecting a suggestion keeps the record (status
        changes to rejected); only an explicit DELETE removes it."""
        self.client.post(
            f"/api/users/{self.user.id}/profile-selections/",
            {"profile_key": "hearing_difficulty", "status": "rejected"},
            format="json",
        )
        self.assertTrue(UserProfileSelection.objects.filter(user=self.user, profile_key="hearing_difficulty").exists())


# --------------------------------------------------------------------------
# Ownership / security -- User A vs. User B, end to end through the real API
# --------------------------------------------------------------------------
class ProfileSelectionOwnershipTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username="selection_owner", password="x")
        self.attacker = User.objects.create_user(username="selection_attacker", password="x")
        self.client.force_authenticate(user=self.owner)
        self.client.post(
            f"/api/users/{self.owner.id}/profile-selections/",
            {"profile_key": "hearing_difficulty", "status": "accepted"},
            format="json",
        )

    def test_user_a_cannot_read_user_bs_suggestions(self):
        self.client.force_authenticate(user=self.attacker)
        response = self.client.get(f"/api/users/{self.owner.id}/profile-suggestions/")
        self.assertEqual(response.status_code, 403)

    def test_user_a_cannot_read_user_bs_selections(self):
        self.client.force_authenticate(user=self.attacker)
        response = self.client.get(f"/api/users/{self.owner.id}/profile-selections/")
        self.assertEqual(response.status_code, 403)

    def test_user_a_cannot_create_selection_for_user_b(self):
        self.client.force_authenticate(user=self.attacker)
        response = self.client.post(
            f"/api/users/{self.owner.id}/profile-selections/",
            {"profile_key": "speech_difficulty", "status": "accepted"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(UserProfileSelection.objects.filter(user=self.owner, profile_key="speech_difficulty").exists())

    def test_user_a_cannot_modify_user_bs_selection(self):
        self.client.force_authenticate(user=self.attacker)
        self.client.post(
            f"/api/users/{self.owner.id}/profile-selections/",
            {"profile_key": "hearing_difficulty", "status": "rejected"},
            format="json",
        )
        stored = UserProfileSelection.objects.get(user=self.owner, profile_key="hearing_difficulty")
        self.assertEqual(stored.status, "accepted")

    def test_user_a_cannot_delete_user_bs_selection(self):
        self.client.force_authenticate(user=self.attacker)
        response = self.client.delete(f"/api/users/{self.owner.id}/profile-selections/hearing_difficulty/")
        self.assertEqual(response.status_code, 403)
        self.assertTrue(UserProfileSelection.objects.filter(user=self.owner, profile_key="hearing_difficulty").exists())

    def test_unauthenticated_cannot_read_private_selections(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(f"/api/users/{self.owner.id}/profile-selections/")
        self.assertEqual(response.status_code, 401)


# --------------------------------------------------------------------------
# Service-level unit tests
# --------------------------------------------------------------------------
class SelectionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="service_selector", password="x")

    def test_upsert_creates_then_updates(self):
        first = upsert_selection(self.user, "hearing_difficulty", UserProfileSelection.STATUS_SUGGESTED)
        second = upsert_selection(self.user, "hearing_difficulty", UserProfileSelection.STATUS_ACCEPTED)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(UserProfileSelection.objects.filter(user=self.user).count(), 1)
        self.assertEqual(second.status, UserProfileSelection.STATUS_ACCEPTED)

    def test_list_selections_scoped_to_user(self):
        other = User.objects.create_user(username="other_service_user", password="x")
        upsert_selection(self.user, "hearing_difficulty", UserProfileSelection.STATUS_ACCEPTED)
        upsert_selection(other, "speech_difficulty", UserProfileSelection.STATUS_ACCEPTED)
        self.assertEqual(list_selections(self.user).count(), 1)

    def test_delete_selection_returns_false_when_nothing_to_delete(self):
        self.assertFalse(delete_selection(self.user, "hearing_difficulty"))

    def test_delete_selection_returns_true_when_deleted(self):
        upsert_selection(self.user, "hearing_difficulty", UserProfileSelection.STATUS_ACCEPTED)
        self.assertTrue(delete_selection(self.user, "hearing_difficulty"))
