"""Series admin registration."""
from django.contrib import admin
from .models import Series


@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'odi_matches_count', 't20_matches_count', 'test_matches_count']
    search_fields = ['name']
    list_filter = ['start_date']
    date_hierarchy = 'start_date'
