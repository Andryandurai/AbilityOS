from django.contrib import admin

from abilities.models import AbilityProfile


@admin.register(AbilityProfile)
class AbilityProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "label", "preferred_modality", "dimensions_summary", "updated_at"]
    readonly_fields = ["updated_at"]
    search_fields = ["user__username", "user__display_name", "label"]

    @admin.display(description="Ability values (level / confidence / source)")
    def dimensions_summary(self, obj):
        non_default = {
            key: val for key, val in obj.dimensions.items() if val.get("source") != "default"
        }
        if not non_default:
            return "all defaults"
        return "; ".join(
            f"{key}: {val.get('level')} ({val.get('confidence', 0):.2f}, {val.get('source')})"
            for key, val in non_default.items()
        )
