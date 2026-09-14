from django.contrib import admin

from tasks.models import Task, TaskStep


class TaskStepInline(admin.TabularInline):
    model = TaskStep
    extra = 0


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["task_id", "name"]
    inlines = [TaskStepInline]
