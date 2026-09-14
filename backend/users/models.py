from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """AbilityOS user account.

    Kept close to Django's default User — the functional data that drives
    adaptation decisions lives on AbilityProfile (abilities app), not here.
    """

    display_name = models.CharField(max_length=120, blank=True)
    is_demo_profile = models.BooleanField(
        default=False,
        help_text="True for the seeded demo personas used to drive the hackathon demo.",
    )

    def __str__(self):
        return self.display_name or self.username


class ConsentRecord(models.Model):
    """What a user has agreed AbilityOS may use, and when.

    AbilityOS never infers or stores ability data without a consent record
    covering the relevant scope — see Part 4 / Part 20 of the project spec.
    """

    SCOPE_INTERACTION_ADAPTATION = "interaction_adaptation"
    SCOPE_BEHAVIOURAL_INFERENCE = "behavioural_inference"

    SCOPE_CHOICES = [
        (SCOPE_INTERACTION_ADAPTATION, "Interaction adaptation"),
        (SCOPE_BEHAVIOURAL_INFERENCE, "Behavioural inference"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="consent")
    granted = models.BooleanField(default=False)
    scope = models.JSONField(default=list, help_text="List of consent scope strings.")
    granted_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Consent<{self.user.username}: {'granted' if self.granted else 'not granted'}>"
