"""Data quality app URL routing."""
from rest_framework.routers import DefaultRouter
from .views import DataQualityReportViewSet, DataConflictLogViewSet

router = DefaultRouter()
router.register(r'reports', DataQualityReportViewSet, basename='dataquality-report')
router.register(r'conflicts', DataConflictLogViewSet, basename='dataquality-conflict')

urlpatterns = router.urls
