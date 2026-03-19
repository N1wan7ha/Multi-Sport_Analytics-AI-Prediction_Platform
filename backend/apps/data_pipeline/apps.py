from django.apps import AppConfig


class DatapipelineConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.data_pipeline'
    label = 'data_pipeline'
