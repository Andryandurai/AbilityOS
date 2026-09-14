from django.contrib import admin

from environments.models import Environment


@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ["environment_id", "name", "source", "created_at"]
