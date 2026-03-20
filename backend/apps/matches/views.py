"""Matches app views — stubs (Phase 2 will add full logic)."""
from django.core.cache import cache
from rest_framework import viewsets, generics, filters
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from .models import Match
from .serializers import MatchSerializer


class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve matches with filtering."""
    queryset = Match.objects.select_related('team1', 'team2', 'venue').prefetch_related('scorecards').order_by('-match_date')
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'format', 'category', 'match_date']
    search_fields = ['name', 'team1__name', 'team2__name']
    ordering_fields = ['match_date', 'created_at']

    def list(self, request, *args, **kwargs):
        query_string = request.META.get('QUERY_STRING', '')
        status = (request.query_params.get('status') or '').lower()
        ttl = 60 if status == 'live' else 6 * 60 * 60
        cache_key = f"api:matches:list:{query_string}"

        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, ttl)
        return response

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        cache_key = f"api:matches:detail:{pk}"

        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        response = super().retrieve(request, *args, **kwargs)
        ttl = 60 if response.data.get('status') == 'live' else 6 * 60 * 60
        cache.set(cache_key, response.data, ttl)
        return response


class LiveMatchesView(generics.ListAPIView):
    """Return live matches only."""
    queryset = Match.objects.filter(status='live').select_related('team1', 'team2')
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def list(self, request, *args, **kwargs):
        cache_key = 'api:matches:live'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        response = super().list(request, *args, **kwargs)
        cache.set(cache_key, response.data, 60)
        return response
