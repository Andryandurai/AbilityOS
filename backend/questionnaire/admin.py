from django.contrib import admin

from questionnaire.models import QuestionnaireQuestion, QuestionnaireResponse, QuestionnaireSession


@admin.register(QuestionnaireQuestion)
class QuestionnaireQuestionAdmin(admin.ModelAdmin):
    list_display = ["key", "version", "order", "question_text"]
    list_filter = ["version"]
    ordering = ["version", "order"]


@admin.register(QuestionnaireSession)
class QuestionnaireSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "version", "started_at", "completed_at"]
    list_filter = ["version"]


@admin.register(QuestionnaireResponse)
class QuestionnaireResponseAdmin(admin.ModelAdmin):
    list_display = ["session", "question", "selected_value", "answered_at"]
