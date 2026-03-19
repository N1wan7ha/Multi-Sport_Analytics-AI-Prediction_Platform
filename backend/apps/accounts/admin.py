"""Accounts admin — use default UserAdmin with extra fields."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'favourite_team', 'is_active', 'is_staff', 'created_at']
    search_fields = ['email', 'username', 'favourite_team']
    ordering = ['email']
    fieldsets = UserAdmin.fieldsets + (
        ('Profile', {'fields': ('bio', 'favourite_team')}),
    )
