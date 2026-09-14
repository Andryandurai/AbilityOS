from django.contrib import admin

from abilities.models import AbilityProfile


@admin.register(AbilityProfile)
class AbilityProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "label", "preferred_modality", "updated_at"]
