"""Matches app views — stubs (Phase 2 will add full logic)."""
from rest_framework import viewsets, generics, filters
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from .models import Match
from .serializers import MatchSerializer


class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve matches with filtering."""
    queryset = Match.objects.select_related('team1', 'team2', 'venue').order_by('-match_date')
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'format', 'category']
    search_fields = ['name', 'team1__name', 'team2__name']
    ordering_fields = ['match_date', 'created_at']


class LiveMatchesView(generics.ListAPIView):
    """Return live matches only."""
    queryset = Match.objects.filter(status='live').select_related('team1', 'team2')
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
