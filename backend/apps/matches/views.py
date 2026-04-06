"""Matches app views with filtering and recommendation scoring."""
from django.core.cache import cache
from datetime import timedelta

from django.db.models import Q, Case, When, Value, IntegerField, FloatField, F
from django.db.models.functions import Coalesce, Greatest
from django.utils import timezone
from rest_framework import viewsets, generics, filters
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from .models import Match
from .serializers import MatchSerializer


FORMAT_ALIASES = {
    'all': '',
    'test': 'test',
    'odi': 'odi',
    'one-day': 'odi',
    'oneday': 'odi',
    't20': 't20',
    't-20': 't20',
    't10': 't10',
}

CATEGORY_ALIASES = {
    'all': '',
    'international': 'international',
    'intl': 'international',
    'franchise': 'franchise',
    'league': 'franchise',
    'domestic': 'domestic',
    'internal': 'domestic',
}


def _normalize_filter_value(raw_value: str, aliases: dict[str, str]) -> str:
    value = (raw_value or '').strip().lower()
    if not value:
        return ''
    return aliases.get(value, value)


def _parse_favorite_team_ids(raw_ids: str) -> list[int]:
    ids: list[int] = []
    for token in (raw_ids or '').split(','):
        token = token.strip()
        if token.isdigit():
            ids.append(int(token))
    # Preserve order while removing duplicates.
    return list(dict.fromkeys(ids))


def _build_format_affinity_map(favorite_team_ids: list[int]) -> dict[str, int]:
    if not favorite_team_ids:
        return {}

    recent_matches = Match.objects.filter(
        status='complete',
        format__isnull=False,
        match_date__isnull=False,
    ).filter(
        Q(team1_id__in=favorite_team_ids) | Q(team2_id__in=favorite_team_ids)
    ).order_by('-match_date')[:24]

    format_counts: dict[str, int] = {}
    for item in recent_matches:
        normalized_format = (item.format or '').strip().lower()
        if not normalized_format:
            continue
        format_counts[normalized_format] = format_counts.get(normalized_format, 0) + 1

    if not format_counts:
        return {}

    # Top formats get the strongest boost to reflect user/team format affinity.
    sorted_formats = sorted(format_counts.items(), key=lambda pair: (-pair[1], pair[0]))
    affinity_points = [20, 12, 6]
    affinity_map: dict[str, int] = {}
    for index, (fmt, _) in enumerate(sorted_formats):
        if index >= len(affinity_points):
            break
        affinity_map[fmt] = affinity_points[index]
    return affinity_map


def _build_recent_performance_map(team_ids: list[int], recent_limit: int = 6) -> dict[int, float]:
    performance_map: dict[int, float] = {}
    for team_id in team_ids:
        recent_completed = list(
            Match.objects.filter(
                status='complete',
                winner__isnull=False,
                match_date__isnull=False,
            ).filter(
                Q(team1_id=team_id) | Q(team2_id=team_id)
            ).order_by('-match_date')[:recent_limit]
        )
        played = len(recent_completed)
        if played == 0:
            performance_map[team_id] = 0.0
            continue
        wins = sum(1 for match in recent_completed if match.winner_id == team_id)
        win_rate = wins / played
        performance_map[team_id] = round(win_rate * 20.0, 2)
    return performance_map


class MatchViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve matches with filtering."""
    queryset = Match.objects.select_related('team1', 'team2', 'venue').prefetch_related('scorecards').order_by('-match_date')
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'category', 'match_date']
    search_fields = ['name', 'team1__name', 'team2__name']
    ordering_fields = ['match_date', 'created_at']

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)

        team = (self.request.query_params.get('team') or '').strip()
        venue = (self.request.query_params.get('venue') or '').strip()
        season = (self.request.query_params.get('season') or '').strip()
        match_format = _normalize_filter_value(self.request.query_params.get('match_format'), FORMAT_ALIASES)
        category = _normalize_filter_value(
            self.request.query_params.get('match_type') or self.request.query_params.get('category'),
            CATEGORY_ALIASES,
        )
        favorite_team_ids = _parse_favorite_team_ids(self.request.query_params.get('favorite_team_ids') or '')
        recommendation_mode = (self.request.query_params.get('recommendation') or '').strip().lower() == 'true'

        if team:
            queryset = queryset.filter(Q(team1__name__icontains=team) | Q(team2__name__icontains=team))

        if venue:
            queryset = queryset.filter(venue__name__icontains=venue)

        if season.isdigit():
            queryset = queryset.filter(match_date__year=int(season))

        if match_format:
            queryset = queryset.filter(format__iexact=match_format)

        if category:
            queryset = queryset.filter(category__iexact=category)

        if recommendation_mode and favorite_team_ids:
            favorite_team_set = set(favorite_team_ids)
            involved_team_ids = set(
                queryset.values_list('team1_id', flat=True)
            ) | set(
                queryset.values_list('team2_id', flat=True)
            )
            involved_team_ids.discard(None)

            format_affinity = _build_format_affinity_map(favorite_team_ids)
            recent_performance = _build_recent_performance_map(list(involved_team_ids))
            today = timezone.now().date()

            format_affinity_case = Case(
                *[
                    When(format__iexact=fmt, then=Value(points))
                    for fmt, points in format_affinity.items()
                ],
                default=Value(0),
                output_field=IntegerField(),
            )
            team1_performance_case = Case(
                *[
                    When(team1_id=team_id, then=Value(points))
                    for team_id, points in recent_performance.items()
                ],
                default=Value(0.0),
                output_field=FloatField(),
            )
            team2_performance_case = Case(
                *[
                    When(team2_id=team_id, then=Value(points))
                    for team_id, points in recent_performance.items()
                ],
                default=Value(0.0),
                output_field=FloatField(),
            )

            queryset = queryset.annotate(
                favorite_rank=Case(
                    When(team1_id__in=favorite_team_set, then=Value(60)),
                    When(team2_id__in=favorite_team_set, then=Value(60)),
                    default=Value(0),
                    output_field=IntegerField(),
                ),
                format_affinity_rank=format_affinity_case,
                team_performance_rank=Greatest(
                    Coalesce(team1_performance_case, Value(0.0)),
                    Coalesce(team2_performance_case, Value(0.0)),
                ),
                recency_rank=Case(
                    When(match_date__isnull=True, then=Value(0)),
                    When(match_date__lt=today, then=Value(0)),
                    When(match_date__lte=today + timedelta(days=2), then=Value(20)),
                    When(match_date__lte=today + timedelta(days=7), then=Value(14)),
                    When(match_date__lte=today + timedelta(days=14), then=Value(8)),
                    default=Value(3),
                    output_field=IntegerField(),
                ),
            ).annotate(
                recommendation_score=(
                    F('favorite_rank')
                    + F('format_affinity_rank')
                    + F('team_performance_rank')
                    + F('recency_rank')
                )
            ).order_by('-recommendation_score', '-favorite_rank', 'match_date', 'id')
        return queryset

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
