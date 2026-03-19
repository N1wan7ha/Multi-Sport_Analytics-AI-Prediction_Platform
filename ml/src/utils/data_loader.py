"""ML utils — data loader from PostgreSQL via Django ORM."""
import os
import sys
import django
import pandas as pd


def setup_django(settings_module: str = 'config.settings.dev'):
    """Bootstrap Django so we can import models in notebooks/scripts."""
    backend_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend')
    )
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', settings_module)
    try:
        django.setup()
    except RuntimeError:
        pass  # Already set up


def load_matches_df() -> pd.DataFrame:
    """Load all completed matches into a pandas DataFrame for model training."""
    setup_django()
    from apps.matches.models import Match

    qs = Match.objects.filter(status='complete').select_related(
        'team1', 'team2', 'venue', 'winner'
    ).values(
        'id', 'format', 'category',
        'team1__name', 'team2__name',
        'venue__name', 'venue__pitch_type', 'venue__avg_first_innings_score',
        'winner__name', 'match_date',
        'toss_winner__name', 'toss_decision',
    )
    df = pd.DataFrame(list(qs))
    if df.empty:
        return df

    # Target column: 1 = team1 wins, 0 = team2 wins
    df['target'] = (df['winner__name'] == df['team1__name']).astype(int)
    df['match_date'] = pd.to_datetime(df['match_date'])
    return df


def load_player_stats_df(match_ids: list = None) -> pd.DataFrame:
    """Load player match stats into a pandas DataFrame."""
    setup_django()
    from apps.players.models import PlayerMatchStats

    qs = PlayerMatchStats.objects.select_related('player', 'match').values(
        'player__name', 'player__role', 'player__country',
        'match_id', 'match__format', 'match__match_date',
        'innings_number',
        'runs_scored', 'balls_faced', 'strike_rate',
        'wickets_taken', 'overs_bowled', 'economy',
        'fours', 'sixes', 'dismissed',
    )
    if match_ids:
        qs = qs.filter(match_id__in=match_ids)

    return pd.DataFrame(list(qs))
