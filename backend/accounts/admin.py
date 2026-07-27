from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Organization information",
            {"fields": ( "organization", "department", "role", ) },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Organization information",
            {"fields": ( "email", "organization", "department", "role",)},
        ),
    )

    list_display = ("id", "email", "username", "organization", "department", "role", "is_active",)