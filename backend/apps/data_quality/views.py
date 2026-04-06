"""Data quality reporting endpoints."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.utils import timezone
from django.db.models import Count, Q, Avg, Max

from .models import (
    DataQualityReport, DataConflictLog, RawSnapshot, CanonicalFieldSource
)
from .serializers import (
    DataQualityReportSerializer, DataConflictLogSerializer
)
from apps.data_quality.utils import generate_data_quality_report


class DataQualityReportViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin endpoint for data quality metrics and insights."""
    queryset = DataQualityReport.objects.all().order_by('-report_date')
    serializer_class = DataQualityReportSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['post'])
    def generate_today_report(self, request):
        """Manually trigger report generation for today."""
        report = generate_data_quality_report()
        serializer = self.get_serializer(report)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def provider_health_trend(self, request):
        """Get provider health trend over last 7 days."""
        from datetime import timedelta
        start_date = timezone.now().date() - timedelta(days=7)
        
        reports = DataQualityReport.objects.filter(
            report_date__gte=start_date
        ).order_by('report_date')
        
        trend = {}
        for report in reports:
            for provider, metrics in report.provider_health.items():
                if provider not in trend:
                    trend[provider] = []
                trend[provider].append({
                    'date': report.report_date.isoformat(),
                    'success_rate': metrics.get('success_rate', 0),
                    'total_calls': metrics.get('total_calls', 0),
                })
        
        return Response(trend)
    
    @action(detail=False, methods=['get'])
    def conflict_summary(self, request):
        """Get conflict resolution summary."""
        total_conflicts = DataConflictLog.objects.count()
        auto_resolved = DataConflictLog.objects.filter(
            resolution_strategy='highest_confidence',
            resolved_at__isnull=False,
        ).count()
        manual_needed = DataConflictLog.objects.filter(
            resolved_at__isnull=True
        ).count()
        
        conflicts_by_type = DataConflictLog.objects.values(
            'entity_type'
        ).annotate(count=Count('id')).order_by('-count')
        
        return Response({
            'total': total_conflicts,
            'auto_resolved': auto_resolved,
            'manual_review_needed': manual_needed,
            'by_entity_type': list(conflicts_by_type),
        })
    
    @action(detail=False, methods=['get'])
    def field_confidence_scores(self, request):
        """Get average confidence scores by entity type and field."""
        entity_type = request.query_params.get('entity_type')
        
        query = CanonicalFieldSource.objects.all()
        if entity_type:
            query = query.filter(entity_type=entity_type)
        
        field_scores = query.values(
            'entity_type', 'field_name'
        ).annotate(
            avg_confidence=Avg('confidence_score'),
            count=Count('id'),
        ).order_by('-avg_confidence')
        
        return Response(list(field_scores))
    
    @action(detail=False, methods=['get'])
    def endpoint_health(self, request):
        """Get health summary of all RapidAPI endpoints."""
        health = RawSnapshot.objects.values(
            'provider', 'endpoint'
        ).annotate(
            total=Count('id'),
            successful=Count('id', filter=Q(status_code=200, is_valid=True)),
            last_call=Max('timestamp'),
        ).order_by('-last_call')
        
        return Response(list(health))


class DataConflictLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin endpoint for viewing and managing data conflicts."""
    queryset = DataConflictLog.objects.all().order_by('-detected_at')
    serializer_class = DataConflictLogSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=False, methods=['get'])
    def unresolved(self, request):
        """Get all unresolved conflicts."""
        unresolved = self.queryset.filter(resolved_at__isnull=True)
        serializer = self.get_serializer(unresolved, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Manually resolve a conflict."""
        conflict = self.get_object()
        resolved_value = request.data.get('resolved_value')
        notes = request.data.get('notes', '')
        
        if not resolved_value:
            return Response(
                {'error': 'resolved_value is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        conflict.resolved_value = resolved_value
        conflict.notes = notes
        conflict.resolved_at = timezone.now()
        conflict.resolved_by = str(request.user)
        conflict.resolution_strategy = 'manual_review'
        conflict.save()
        
        serializer = self.get_serializer(conflict)
        return Response(serializer.data)
