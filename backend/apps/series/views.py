from django.db.models import Q
from rest_framework import viewsets, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.matches.models import Match
from apps.matches.serializers import MatchSerializer
from .models import Series


class SeriesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Series
        fields = '__all__'


class SeriesViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Series.objects.all()
    serializer_class = SeriesSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['get'], url_path='matches')
    def matches(self, request, pk=None):
        current_series = self.get_object()
        queryset = Match.objects.select_related('team1', 'team2', 'venue').prefetch_related('scorecards').filter(
            Q(raw_data__seriesName__iexact=current_series.name)
            | Q(raw_data__series_name__iexact=current_series.name)
            | Q(raw_data__seriesId=str(current_series.cricapi_id))
            | Q(raw_data__series_id=str(current_series.cricapi_id))
        ).order_by('-match_date')

        page = self.paginate_queryset(queryset)
        serializer = MatchSerializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
