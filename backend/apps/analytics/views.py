from django.db.models import Q, Count, Sum, Avg
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from apps.matches.models import Match, Team
from apps.players.models import Player, PlayerMatchStats
import requests
from django.conf import settings
import logging
import re
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


FORMAT_ALIASES = {
    't20': {'t20', 't20i', 'it20'},
    'odi': {'odi'},
    'test': {'test'},
}

CATEGORY_ALIASES = {
    'international': {'international', 'internal', 'int'},
    'franchise': {'franchise', 'league'},
    'domestic': {'domestic'},
}


def _normalized_filter(value):
    return (value or '').strip().lower()


def _parse_requested_filters(request):
    requested_format = _normalized_filter(request.query_params.get('format'))
    requested_category = _normalized_filter(
        request.query_params.get('category') or request.query_params.get('match_type')
    )
    return requested_format, requested_category


def _apply_match_filters(queryset, requested_format, requested_category):
    if requested_format and requested_format != 'all':
        format_values = FORMAT_ALIASES.get(requested_format, {requested_format})
        queryset = queryset.filter(format__in=list(format_values))

    if requested_category and requested_category != 'all':
        category_values = CATEGORY_ALIASES.get(requested_category, {requested_category})
        queryset = queryset.filter(category__in=list(category_values))

    return queryset

class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        return Response({
            'total_matches': Match.objects.count(),
            'live_matches': Match.objects.filter(status='live').count(),
            'upcoming_matches': Match.objects.filter(status='upcoming').count(),
            'total_players': Player.objects.count(),
        })


class TeamAnalyticsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, team_name):
        query = (team_name or '').strip()
        if not query:
            raise NotFound('Team name is required.')

        team = Team.objects.filter(
            Q(name__iexact=query) | Q(short_name__iexact=query) | Q(country__iexact=query)
        ).order_by('-is_international', 'name').first()

        if team is None:
            team = Team.objects.filter(
                Q(name__icontains=query) | Q(short_name__icontains=query) | Q(country__icontains=query)
            ).order_by('-is_international', 'name').first()

        if team is None:
            raise NotFound('Team not found.')

        requested_format, requested_category = _parse_requested_filters(request)

        all_matches = Match.objects.filter(Q(team1=team) | Q(team2=team))
        all_matches = _apply_match_filters(all_matches, requested_format, requested_category)
        completed = all_matches.filter(status='complete')
        wins = completed.filter(winner=team).count()
        losses = completed.exclude(winner=team).exclude(winner__isnull=True).count()
        ties_or_nr = completed.filter(winner__isnull=True).count()

        total_completed = completed.count()
        win_rate = round((wins / total_completed) * 100, 2) if total_completed else 0.0

        recent_results = []
        for match in completed.order_by('-match_date', '-id')[:5]:
            if match.winner_id == team.id:
                outcome = 'W'
            elif match.winner_id is None:
                outcome = 'N'
            else:
                outcome = 'L'
            recent_results.append({
                'match_id': match.id,
                'match_name': match.name,
                'match_date': match.match_date,
                'outcome': outcome,
            })

        by_format_rows = completed.values('format').annotate(total=Count('id')).order_by('format')
        by_format = {row['format']: row['total'] for row in by_format_rows}

        return Response({
            'team': team.name,
            'total_matches': all_matches.count(),
            'matches_total': all_matches.count(),
            'completed_matches': total_completed,
            'wins': wins,
            'losses': losses,
            'ties_or_no_result': ties_or_nr,
            'win_rate': win_rate,
            'win_rate_percent': win_rate,
            'recent_form': recent_results,
            'by_format': by_format,
            'applied_filters': {
                'format': requested_format or 'all',
                'category': requested_category or 'all',
            },
        })


class PlayerAnalyticsView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, player_id):
        player = get_object_or_404(Player, pk=player_id)
        requested_format, requested_category = _parse_requested_filters(request)

        stats = PlayerMatchStats.objects.filter(player=player).select_related('match')
        stats = _apply_match_filters(stats, requested_format, requested_category)
        stats = stats.order_by('-match__match_date', '-id')

        agg = stats.aggregate(
            matches=Count('id'),
            total_runs=Sum('runs_scored'),
            total_wickets=Sum('wickets_taken'),
            batting_avg=Avg('runs_scored'),
            strike_rate_avg=Avg('strike_rate'),
            economy_avg=Avg('economy'),
        )

        recent = []
        for row in stats[:10]:
            recent.append({
                'match_id': row.match_id,
                'match_name': row.match.name,
                'match_date': row.match.match_date,
                'runs_scored': row.runs_scored,
                'wickets_taken': row.wickets_taken,
                'strike_rate': row.strike_rate,
                'economy': row.economy,
            })

        return Response({
            'player_id': player.id,
            'player_name': player.name,
            'player': {'id': player.id, 'name': player.name},
            'matches_played': agg['matches'] or 0,
            'matches': agg['matches'] or 0,
            'total_runs': agg['total_runs'] or 0,
            'total_wickets': agg['total_wickets'] or 0,
            'batting_average': round(agg['batting_avg'] or 0.0, 2),
            'avg_runs': round(agg['batting_avg'] or 0.0, 2),
            'avg_wickets': round(((agg['total_wickets'] or 0) / (agg['matches'] or 1)) if (agg['matches'] or 0) else 0.0, 2),
            'average_strike_rate': round(agg['strike_rate_avg'] or 0.0, 2),
            'average_economy': round(agg['economy_avg'] or 0.0, 2),
            'recent_performances': recent,
            'applied_filters': {
                'format': requested_format or 'all',
                'category': requested_category or 'all',
            },
        })


class InternationalTeamsView(APIView):
    """List all international teams with recent form."""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        teams = Team.objects.filter(is_international=True).order_by('name')

        result = []
        for team in teams:
            all_matches = Match.objects.filter(
                Q(team1=team) | Q(team2=team),
                category__in=['international', 'internal', 'int']
            )

            if not all_matches.exists():
                continue

            matches = all_matches.order_by('-match_date', '-id')[:5]
            recent_form = []
            for match in matches:
                if match.status == 'complete':
                    if match.winner_id == team.id:
                        recent_form.append('W')
                    elif match.winner_id is None:
                        recent_form.append('N')
                    else:
                        recent_form.append('L')
            
            completed = all_matches.filter(status='complete')
            wins = completed.filter(winner=team).count()
            losses = completed.exclude(winner=team).exclude(winner__isnull=True).count()
            total = completed.count()
            win_rate = round((wins / total) * 100, 1) if total > 0 else 0.0

            result.append({
                'id': team.id,
                'name': team.name,
                'short_name': team.short_name,
                'country': team.country,
                'logo_url': team.logo_url,
                'total_matches': total,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'recent_form': ''.join(recent_form[:5]),
            })

        result.sort(key=lambda item: (item.get('total_matches', 0), item.get('win_rate', 0.0)), reverse=True)
        return Response({'count': len(result), 'results': result})


class TopPlayersView(APIView):
    """List top performing players by runs, wickets, or recent matches."""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        metric = request.query_params.get('metric', 'matches').lower()
        limit = int(request.query_params.get('limit', 10))
        
        if metric == 'runs':
            stats = PlayerMatchStats.objects.filter(runs_scored__isnull=False).values('player').annotate(
                total_runs=Sum('runs_scored'),
                matches=Count('id')
            ).filter(matches__gte=3).order_by('-total_runs')[:limit]
        elif metric == 'wickets':
            stats = PlayerMatchStats.objects.filter(wickets_taken__isnull=False).values('player').annotate(
                total_wickets=Sum('wickets_taken'),
                matches=Count('id')
            ).filter(matches__gte=3).order_by('-total_wickets')[:limit]
        else:
            stats = PlayerMatchStats.objects.values('player').annotate(
                total_matches=Count('id')
            ).order_by('-total_matches')[:limit]
        
        result = []
        for stat in stats:
            player = Player.objects.get(pk=stat['player'])
            data = {
                'id': player.id,
                'name': player.name,
                'country': player.country,
                'role': player.role,
                'team': {'id': player.team.id, 'name': player.team.name} if player.team else None,
            }
            if metric == 'runs':
                data['total_runs'] = stat.get('total_runs', 0)
                data['matches'] = stat.get('matches', 0)
            elif metric == 'wickets':
                data['total_wickets'] = stat.get('total_wickets', 0)
                data['matches'] = stat.get('matches', 0)
            else:
                data['matches'] = stat.get('total_matches', 0)
            result.append(data)
        
        return Response({'count': len(result), 'results': result})


class CricketNewsView(APIView):
    """Fetch cricket news from external API."""
    permission_classes = [IsAuthenticatedOrReadOnly]

    @staticmethod
    def _to_image_url(raw_image):
        if not raw_image:
            return ''
        image_value = str(raw_image).strip()
        if not image_value:
            return ''
        if image_value.startswith('http://') or image_value.startswith('https://'):
            return image_value
        if image_value.isdigit():
            # Prefer a larger variant for better card quality in the Home newsroom.
            return f"https://www.cricbuzz.com/a/img/v1/595x396/i1/c{image_value}/i.jpg"
        return image_value

    @staticmethod
    def _story_category(title):
        lowered = (title or '').lower()
        if 'rank' in lowered or 'table' in lowered:
            return 'rankings'
        if 'opinion' in lowered or 'analysis' in lowered or 'preview' in lowered:
            return 'editorial'
        if 'trend' in lowered or 'viral' in lowered or 'hot' in lowered:
            return 'trending'
        return 'top'

    @staticmethod
    def _first_image_from_html(text):
        if not text:
            return ''
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', text, flags=re.IGNORECASE)
        return match.group(1).strip() if match else ''

    @staticmethod
    def _clean_html(text):
        if not text:
            return ''
        no_tags = re.sub(r'<[^>]+>', ' ', str(text))
        return re.sub(r'\s+', ' ', no_tags).strip()

    def _extract_rss_rows(self, xml_text, source_name='RSS Feed'):
        try:
            root = ET.fromstring(xml_text)
        except Exception:
            return []

        rows = []
        items = root.findall('.//item')
        for index, item in enumerate(items):
            title = (item.findtext('title') or '').strip()
            if not title:
                continue

            description = (item.findtext('description') or '').strip()
            link = (item.findtext('link') or '/matches').strip() or '/matches'
            pub_date = (item.findtext('pubDate') or '').strip()

            media_content = item.find('{http://search.yahoo.com/mrss/}content')
            media_thumbnail = item.find('{http://search.yahoo.com/mrss/}thumbnail')

            image = ''
            if media_content is not None:
                image = (media_content.attrib.get('url') or '').strip()
            if not image and media_thumbnail is not None:
                image = (media_thumbnail.attrib.get('url') or '').strip()
            if not image:
                image = self._first_image_from_html(description)

            summary = self._clean_html(description) or 'Latest cricket update'
            if len(summary) > 220:
                summary = summary[:217].rstrip() + '...'

            rows.append({
                'id': f"rss-{source_name.lower().replace(' ', '-')}-{index + 1}",
                'title': title,
                'summary': summary,
                'image': image,
                'link': link,
                'source': source_name,
                'timestamp': pub_date,
                'category': self._story_category(title),
            })

            if len(rows) >= 30:
                break

        return rows

    def _fetch_external_rss_news(self):
        feeds = [
            ('Google News', 'https://news.google.com/rss/search?q=cricket&hl=en-IN&gl=IN&ceid=IN:en'),
            ('ESPN Cricinfo', 'https://www.espncricinfo.com/rss/content/story/feeds/0.xml'),
        ]

        all_rows = []
        for source_name, feed_url in feeds:
            try:
                response = requests.get(feed_url, timeout=8)
                if response.status_code != 200:
                    continue
                all_rows.extend(self._extract_rss_rows(response.text, source_name=source_name))
            except Exception:
                continue

        return all_rows

    def _fallback_news(self):
        return [
            {'id': 1, 'title': 'Latest Cricket Match Highlights', 'summary': 'Watch the latest international cricket match highlights and analysis.', 'image': '', 'link': '/matches', 'source': 'MatchMind', 'timestamp': '', 'category': 'top'},
            {'id': 2, 'title': 'Team Performance Analytics', 'summary': 'Explore in-depth analytics of international cricket teams performance.', 'image': '', 'link': '/analytics', 'source': 'MatchMind', 'timestamp': '', 'category': 'editorial'},
            {'id': 3, 'title': 'Player Stats and Records', 'summary': 'Browse comprehensive player statistics and recent performances.', 'image': '', 'link': '/players', 'source': 'MatchMind', 'timestamp': '', 'category': 'rankings'},
            {'id': 4, 'title': 'Trending Cricket Talking Points', 'summary': 'Catch up with trending stories, team updates, and tournament talking points.', 'image': '', 'link': '/home', 'source': 'MatchMind', 'timestamp': '', 'category': 'trending'},
            {'id': 5, 'title': 'T20 World Cup Update', 'summary': 'Latest news and updates from the ongoing T20 World Cup tournament.', 'image': '', 'link': '/matches', 'source': 'Cricket.com', 'timestamp': '', 'category': 'top'},
            {'id': 6, 'title': 'ODI Series Analysis', 'summary': 'In-depth analysis of ongoing ODI series and match predictions.', 'image': '', 'link': '/analytics', 'source': 'Cricket.com', 'timestamp': '', 'category': 'editorial'},
            {'id': 7, 'title': 'Emerging Player Rankings', 'summary': 'Top emerging cricket players to watch this season.', 'image': '', 'link': '/players', 'source': 'MatchMind', 'timestamp': '', 'category': 'rankings'},
            {'id': 8, 'title': 'Viral Cricket Moments', 'summary': 'The most viral and talked-about moments from recent matches.', 'image': '', 'link': '/home', 'source': 'Cricket.com', 'timestamp': '', 'category': 'trending'},
            {'id': 9, 'title': 'Test Series Schedule', 'summary': 'Complete schedule and fixtures for upcoming test cricket series.', 'image': '', 'link': '/matches', 'source': 'MatchMind', 'timestamp': '', 'category': 'top'},
            {'id': 10, 'title': 'Franchise League News', 'summary': 'Breaking news from IPL, BBL, and other domestic franchise leagues.', 'image': '', 'link': '/analytics', 'source': 'Cricket.com', 'timestamp': '', 'category': 'editorial'},
            {'id': 11, 'title': 'Player Injury Updates', 'summary': 'Latest updates on player injuries and rehabilitation progress.', 'image': '', 'link': '/players', 'source': 'MatchMind', 'timestamp': '', 'category': 'rankings'},
            {'id': 12, 'title': 'Match Predictions & Odds', 'summary': 'Expert predictions and analysis for upcoming cricket matches.', 'image': '', 'link': '/home', 'source': 'Cricket.com', 'timestamp': '', 'category': 'trending'},
            {'id': 13, 'title': 'International Cricket Rankings', 'summary': 'Current ICC rankings for all formats and player categories.', 'image': '', 'link': '/analytics', 'source': 'MatchMind', 'timestamp': '', 'category': 'rankings'},
            {'id': 14, 'title': 'Upcoming Tournaments', 'summary': 'Overview of major cricket tournaments scheduled for this year.', 'image': '', 'link': '/matches', 'source': 'Cricket.com', 'timestamp': '', 'category': 'top'},
            {'id': 15, 'title': 'Coach & Team Strategy', 'summary': 'Analysis of coaching changes and team strategic planning.', 'image': '', 'link': '/analytics', 'source': 'MatchMind', 'timestamp': '', 'category': 'editorial'},
        ]

    def _extract_news_rows(self, payload):
        rows = []

        if isinstance(payload, dict):
            for key in ('data', 'storyList', 'stories', 'news'):
                value = payload.get(key)
                if isinstance(value, list):
                    rows.extend(value)

        if isinstance(payload, list):
            rows.extend(payload)

        parsed = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue

            candidate = row.get('story') if isinstance(row.get('story'), dict) else row
            if not isinstance(candidate, dict):
                continue

            title = (
                candidate.get('headline')
                or candidate.get('title')
                or candidate.get('hline')
                or row.get('title')
                or row.get('headline')
                or ''
            )
            if not title:
                continue

            summary = (
                candidate.get('intro')
                or candidate.get('summary')
                or candidate.get('description')
                or row.get('intro')
                or row.get('summary')
                or 'Latest cricket update'
            )
            story_id = candidate.get('id') or row.get('id') or index + 1
            image = (
                candidate.get('imageId')
                or candidate.get('image_id')
                or candidate.get('image')
                or row.get('imageId')
                or row.get('image')
            )
            timestamp = (
                candidate.get('pubTime')
                or candidate.get('publishTime')
                or candidate.get('timestamp')
                or row.get('pubTime')
                or ''
            )

            inferred_category = self._story_category(title)

            parsed.append({
                'id': story_id,
                'title': str(title).strip(),
                'summary': str(summary).strip(),
                'image': self._to_image_url(image),
                'link': '/matches',
                'source': 'Cricbuzz',
                'timestamp': str(timestamp),
                'category': inferred_category,
            })

            if len(parsed) >= 50:
                break

        return parsed

    def get(self, request):
        try:
            host = getattr(settings, 'CRICBUZZ_RAPIDAPI_HOST', 'cricbuzz-cricket2.p.rapidapi.com')
            key = getattr(settings, 'CRICBUZZ_RAPIDAPI_KEY', '')
            
            headers = {
                'x-rapidapi-key': key,
                'x-rapidapi-host': host,
            }
            
            # Try to fetch news with pagination offset
            offset = int(request.query_params.get('offset', 0))
            url = f"https://{host}/news/v1/index"
            params = {} if offset == 0 else {'offset': offset}
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            result = self._extract_news_rows(data)
            
            # If we got few results, try additional news endpoints
            if len(result) < 15:
                try:
                    # Try match news endpoint as well
                    match_url = f"https://{host}/matches/v1/news"
                    match_resp = requests.get(match_url, headers=headers, timeout=10)
                    if match_resp.status_code == 200:
                        match_data = match_resp.json()
                        additional = self._extract_news_rows(match_data)
                        result.extend(additional[:20])  # Add up to 20 more
                except:
                    pass  # Silently skip if additional endpoint fails

            # Add RSS-based stories from additional public sources.
            if len(result) < 35:
                rss_rows = self._fetch_external_rss_news()
                existing_titles = {str(item.get('title', '')).strip().lower() for item in result}
                for row in rss_rows:
                    title_key = str(row.get('title', '')).strip().lower()
                    if title_key and title_key not in existing_titles:
                        result.append(row)
                        existing_titles.add(title_key)
                    if len(result) >= 50:
                        break
            
            # Top up with fallback stories if still short on content
            if len(result) < 15:
                fallback = self._fallback_news()
                for fb_story in fallback:
                    # Only add if not already present
                    if not any(r.get('title') == fb_story['title'] for r in result):
                        result.append(fb_story)
            
            if not result:
                logger.warning('News API response parsed but no usable stories found. Using local news feed.')
                result = self._fallback_news()
            
            return Response({'count': len(result), 'results': result[:50]})  # Return up to 50 stories
        except Exception as e:
            logger.warning(f'Failed to fetch cricket news: {str(e)}')
            result = self._fallback_news()
            return Response({'count': len(result), 'results': result})


class InternationalStandingsView(APIView):
    """Get international cricket standings and rankings."""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        format_type = request.query_params.get('format', 'test').lower()
        
        try:
            host = getattr(settings, 'CRICBUZZ_RAPIDAPI_HOST', 'cricbuzz-cricket2.p.rapidapi.com')
            key = getattr(settings, 'CRICBUZZ_RAPIDAPI_KEY', '')
            
            headers = {
                'x-rapidapi-key': key,
                'x-rapidapi-host': host,
            }
            
            url = f"https://{host}/stats/v1/rankings/batsmen?formatType={format_type}"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            rankings = data.get('data', []) if isinstance(data, dict) else data
            
            if isinstance(rankings, list):
                result = []
                for rank_data in rankings[:15]:
                    result.append({
                        'rank': rank_data.get('rank', 0),
                        'player': rank_data.get('name', rank_data.get('player', 'Unknown')),
                        'country': rank_data.get('country', ''),
                        'rating': rank_data.get('rating', 0),
                        'matches': rank_data.get('matches', 0),
                        'format': format_type,
                    })
                return Response({'count': len(result), 'format': format_type, 'results': result})
        except Exception as e:
            logger.warning(f'Failed to fetch international standings: {str(e)}')
        
        teams = Team.objects.filter(is_international=True).order_by('name')[:15]
        result = []
        for i, team in enumerate(teams, 1):
            completed = Match.objects.filter(Q(team1=team) | Q(team2=team), status='complete')
            wins = completed.filter(winner=team).count()
            total = completed.count()
            result.append({
                'rank': i,
                'player': team.name,
                'country': team.country or '',
                'rating': wins,
                'matches': total,
                'format': format_type,
            })
        
        return Response({'count': len(result), 'format': format_type, 'results': result})

