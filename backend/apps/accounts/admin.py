"""Accounts admin — use default UserAdmin with extra fields."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserFavouriteTeam, NotificationDispatch


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'favourite_team', 'is_active', 'is_staff', 'created_at']
    search_fields = ['email', 'username', 'favourite_team']
    ordering = ['email']
    fieldsets = UserAdmin.fieldsets + (
        ('Profile', {'fields': ('bio', 'favourite_team')}),
    )


@admin.register(UserFavouriteTeam)
class UserFavouriteTeamAdmin(admin.ModelAdmin):
    list_display = ['user', 'team', 'created_at']
    search_fields = ['user__email', 'user__username', 'team__name']


@admin.register(NotificationDispatch)
class NotificationDispatchAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'match', 'prediction_job', 'sent_at']
    search_fields = ['user__email', 'notification_type']
