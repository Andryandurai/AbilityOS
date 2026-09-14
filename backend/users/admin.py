from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from users.models import ConsentRecord, User


@admin.register(User)
class AbilityOSUserAdmin(UserAdmin):
    list_display = ["username", "display_name", "is_demo_profile", "is_staff"]


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ["user", "granted", "granted_at", "updated_at"]
