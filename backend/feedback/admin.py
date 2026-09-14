from django.contrib import admin

from feedback.models import Feedback, InteractionSession


@admin.register(InteractionSession)
class InteractionSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "task", "status", "baseline_mode", "ai_used", "is_seed", "created_at"]
    list_filter = ["status", "baseline_mode", "ai_used", "is_seed"]


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ["session", "completed", "errors", "time_seconds", "assistance_requested"]
