from django.contrib import admin

from adaptations.models import Adaptation, AdaptationResult


@admin.register(Adaptation)
class AdaptationAdmin(admin.ModelAdmin):
    list_display = ["name", "display_name", "risk_level", "accessibility_benefit", "interaction_cost", "risk", "enabled"]
    list_filter = ["risk_level", "enabled"]


@admin.register(AdaptationResult)
class AdaptationResultAdmin(admin.ModelAdmin):
    list_display = ["session", "adaptation", "score", "source", "approved", "applied"]
    list_filter = ["source", "approved", "applied"]
