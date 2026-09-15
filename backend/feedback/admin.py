from django.contrib import admin

from feedback.models import Feedback, InteractionEvent, InteractionSession


@admin.register(InteractionSession)
class InteractionSessionAdmin(admin.ModelAdmin):
    list_display = [
        "id", "user", "task", "status", "baseline_mode", "ai_used", "assistance_count", "is_seed", "created_at",
    ]
    list_filter = ["status", "baseline_mode", "ai_used", "is_seed"]


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = [
        "session", "completed", "errors", "time_seconds", "assistance_requested", "ease_rating",
        "adaptation_helpfulness",
    ]


@admin.register(InteractionEvent)
class InteractionEventAdmin(admin.ModelAdmin):
    list_display = ["id", "session", "event_type", "step", "control_id", "created_at"]
    list_filter = ["event_type"]
