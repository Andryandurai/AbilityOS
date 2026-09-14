from django.contrib import admin

from barriers.models import Barrier


@admin.register(Barrier)
class BarrierAdmin(admin.ModelAdmin):
    list_display = ["session", "barrier_type", "ability_dimension", "severity", "confidence"]
    list_filter = ["barrier_type"]
