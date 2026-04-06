from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.matches.models import Match, MatchScorecard, Team, Venue
from apps.players.models import Player, PlayerMatchStats
from ml_engine.training import train_models_for_year_range, train_models_from_matches


LEGAL_EXTRAS_WICKET_EXCLUDE = {'run out', 'retired hurt', 'obstructing the field'}


@dataclass
class InningAggregate:
    innings_number: int
    batting_team: str
    total_runs: int = 0
    wickets: int = 0
    legal_balls: int = 0


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _normalize_format(match_type: str, event: str) -> str:
    text = (match_type or event or '').strip().lower()
    if 'test' in text:
        return 'test'
    if 'odi' in text:
        return 'odi'
    if 't20' in text:
        return 't20'
    if 't10' in text:
        return 't10'
    return 'other'


def _infer_category(event: str) -> str:
    text = (event or '').strip().lower()
    if any(token in text for token in ('ipl', 'bbl', 'psl', 'cpl', 'league', 'premier')):
        return 'franchise'
    if any(token in text for token in ('ranji', 'county', 'domestic', 'shield')):
        return 'domestic'
    return 'international'


def _parse_date(date_values: list[str]) -> datetime.date | None:
    for value in date_values:
        for fmt in ('%Y/%m/%d', '%Y-%m-%d'):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


class Command(BaseCommand):
    help = 'Seed completed matches from Cricsheet CSV/JSON files and optionally train models.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dataset-dir',
            default='',
            help='Directory containing Cricsheet CSV/JSON files. Defaults to resources/dataset.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Optional file limit for partial import.',
        )
        parser.add_argument(
            '--train',
            action='store_true',
            help='Run model training after import completes.',
        )
        parser.add_argument(
            '--walk-forward',
            action='store_true',
            help='Run walk-forward trainer after standard training.',
        )
        parser.add_argument(
            '--train-yearly',
            action='store_true',
            help='Train model in yearly chunks instead of one full training run.',
        )
        parser.add_argument(
            '--start-year',
            type=int,
            default=0,
            help='Start year for yearly training (inclusive).',
        )
        parser.add_argument(
            '--end-year',
            type=int,
            default=0,
            help='End year for yearly training (inclusive).',
        )
        parser.add_argument(
            '--version-prefix',
            default='v2.1-cricsheet',
            help='Model version prefix used for yearly model artifacts.',
        )

    def handle(self, *args, **options):
        dataset_dir = options.get('dataset_dir') or ''
        if dataset_dir:
            root = Path(dataset_dir)
        else:
            root = Path(settings.BASE_DIR).parent / 'resources' / 'dataset'

        if not root.exists() or not root.is_dir():
            self.stderr.write(self.style.ERROR(f'Dataset directory not found: {root}'))
            return

        files = sorted([*root.glob('*.csv'), *root.glob('*.json')])
        if not files:
            self.stderr.write(self.style.ERROR(f'No CSV/JSON files found in: {root}'))
            return

        limit = int(options.get('limit') or 0)
        if limit > 0:
            files = files[:limit]

        imported = 0
        updated = 0
        skipped = 0

        self.stdout.write(self.style.NOTICE(f'Importing {len(files)} Cricsheet files from {root}'))

        for idx, csv_path in enumerate(files, start=1):
            try:
                created = self._import_file(csv_path)
                if created:
                    imported += 1
                else:
                    updated += 1
            except Exception as exc:
                skipped += 1
                self.stderr.write(f'[{idx}/{len(files)}] skip {csv_path.name}: {exc}')

            if idx % 250 == 0:
                self.stdout.write(
                    f'Progress {idx}/{len(files)} | created={imported} updated={updated} skipped={skipped}'
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Cricsheet import done: created={imported} updated={updated} skipped={skipped}'
            )
        )

        if options.get('train'):
            if options.get('train_yearly'):
                self._train_yearly(options)
            else:
                summary = train_models_from_matches(settings.ML_MODEL_PATH, version='v2.1-cricsheet')
                self.stdout.write(
                    self.style.SUCCESS(
                        'Training complete '
                        f"| samples={summary.sample_count} model={summary.model_type} "
                        f"acc={summary.accuracy} auc={summary.auc_roc} brier={summary.brier_score}"
                    )
                )

            if options.get('walk_forward'):
                try:
                    from ml_engine.walk_forward_trainer import train_walk_forward_models

                    wf = train_walk_forward_models(settings.ML_MODEL_PATH, version='v2.1-walk-forward')
                    self.stdout.write(self.style.SUCCESS(f'Walk-forward result: {wf}'))
                except Exception as exc:
                    self.stderr.write(self.style.WARNING(f'Walk-forward skipped: {exc}'))

    def _train_yearly(self, options: dict[str, Any]) -> None:
        start_year = int(options.get('start_year') or 0)
        end_year = int(options.get('end_year') or 0)
        version_prefix = str(options.get('version_prefix') or 'v2.1-cricsheet').strip()

        if not start_year or not end_year:
            years = list(
                Match.objects.filter(
                    status='complete',
                    match_date__isnull=False,
                ).values_list('match_date__year', flat=True).distinct().order_by('match_date__year')
            )
            if not years:
                self.stderr.write(self.style.WARNING('No complete matches found for yearly training.'))
                return
            start_year = int(years[0])
            end_year = int(years[-1])

        if start_year > end_year:
            start_year, end_year = end_year, start_year

        self.stdout.write(
            self.style.NOTICE(
                f'Yearly training from {start_year} to {end_year} with prefix {version_prefix}'
            )
        )

        summaries = []
        for year in range(start_year, end_year + 1):
            version = f'{version_prefix}-y{year}'
            summary = train_models_for_year_range(
                settings.ML_MODEL_PATH,
                version=version,
                start_year=year,
                end_year=year,
            )
            summaries.append(summary)
            self.stdout.write(
                f'  year={year} version={version} samples={summary.sample_count} '
                f'model={summary.model_type} acc={summary.accuracy} auc={summary.auc_roc} brier={summary.brier_score}'
            )

        successful = sum(1 for s in summaries if s.model_type == 'sklearn_ensemble')
        self.stdout.write(
            self.style.SUCCESS(
                f'Yearly training complete: {len(summaries)} years processed, {successful} sklearn bundles saved.'
            )
        )

    @transaction.atomic
    def _import_file(self, csv_path: Path) -> bool:
        if csv_path.suffix.lower() == '.json':
            return self._import_json_file(csv_path)

        info_multi: dict[str, list[str]] = defaultdict(list)
        players_by_team: dict[str, set[str]] = defaultdict(set)

        innings_totals: dict[int, InningAggregate] = {}
        batting_stats: dict[tuple[int, str], dict[str, int]] = defaultdict(
            lambda: {'runs': 0, 'balls': 0, 'fours': 0, 'sixes': 0, 'dismissed': 0}
        )
        bowling_stats: dict[tuple[int, str], dict[str, float]] = defaultdict(
            lambda: {'legal_balls': 0.0, 'runs_conceded': 0.0, 'wickets': 0.0}
        )

        with csv_path.open('r', encoding='utf-8', newline='') as handle:
            reader = csv.reader(handle)
            for row in reader:
                if not row:
                    continue

                rec_type = (row[0] or '').strip().lower()
                if rec_type == 'info':
                    if len(row) < 3:
                        continue
                    key = (row[1] or '').strip().lower()

                    if key == 'player' and len(row) >= 4:
                        team_name = row[2].strip()
                        player_name = row[3].strip()
                        if team_name and player_name:
                            players_by_team[team_name].add(player_name)
                    else:
                        value = row[2].strip()
                        if value:
                            info_multi[key].append(value)

                elif rec_type == 'ball':
                    if len(row) < 9:
                        continue

                    innings_number = _to_int(row[1])
                    batting_team = (row[3] or '').strip()
                    striker = (row[4] or '').strip()
                    bowler = (row[6] or '').strip()

                    batter_runs = _to_int(row[7])
                    extras = _to_int(row[8])
                    wide = _to_int(row[9]) if len(row) > 9 else 0
                    no_ball = _to_int(row[10]) if len(row) > 10 else 0
                    wicket_type = (row[14] if len(row) > 14 else '').strip().lower()
                    wicket_player = (row[15] if len(row) > 15 else '').strip()

                    inning = innings_totals.get(innings_number)
                    if inning is None:
                        inning = InningAggregate(innings_number=innings_number, batting_team=batting_team)
                        innings_totals[innings_number] = inning

                    inning.total_runs += batter_runs + extras
                    is_legal = wide == 0 and no_ball == 0
                    if is_legal:
                        inning.legal_balls += 1

                    if wicket_type:
                        inning.wickets += 1

                    if striker:
                        key = (innings_number, striker)
                        batting_stats[key]['runs'] += batter_runs
                        if is_legal:
                            batting_stats[key]['balls'] += 1
                        if batter_runs == 4:
                            batting_stats[key]['fours'] += 1
                        if batter_runs == 6:
                            batting_stats[key]['sixes'] += 1
                        if wicket_player and wicket_player == striker:
                            batting_stats[key]['dismissed'] = 1

                    if bowler:
                        key = (innings_number, bowler)
                        if is_legal:
                            bowling_stats[key]['legal_balls'] += 1
                        bowling_stats[key]['runs_conceded'] += batter_runs + extras
                        if wicket_type and wicket_type not in LEGAL_EXTRAS_WICKET_EXCLUDE:
                            bowling_stats[key]['wickets'] += 1

        teams = info_multi.get('team', [])
        if len(teams) < 2:
            raise ValueError('missing team entries')

        team1_name = teams[0]
        team2_name = teams[1]
        team1, _ = Team.objects.get_or_create(
            name=team1_name,
            defaults={
                'short_name': team1_name[:10].upper(),
                'country': team1_name,
                'is_international': True,
                'primary_source': 'cricsheet_csv',
                'confidence_score': 92,
                'source_urls': [{'provider': 'cricsheet_csv'}],
            },
        )
        team2, _ = Team.objects.get_or_create(
            name=team2_name,
            defaults={
                'short_name': team2_name[:10].upper(),
                'country': team2_name,
                'is_international': True,
                'primary_source': 'cricsheet_csv',
                'confidence_score': 92,
                'source_urls': [{'provider': 'cricsheet_csv'}],
            },
        )

        venue_name = (info_multi.get('venue') or ['Unknown venue'])[0]
        city_name = (info_multi.get('city') or [''])[0]
        venue, _ = Venue.objects.get_or_create(
            name=venue_name,
            defaults={'city': city_name, 'country': '', 'pitch_type': 'balanced'},
        )

        match_type = (info_multi.get('match_type') or [''])[0]
        event_name = (info_multi.get('event') or [''])[0]
        fmt = _normalize_format(match_type=match_type, event=event_name)
        category = _infer_category(event=event_name)
        match_date = _parse_date(info_multi.get('date', []))

        winner_name = (info_multi.get('winner') or [''])[0]
        winner_obj = None
        if winner_name:
            winner_obj = Team.objects.filter(name__iexact=winner_name).first()

        toss_winner_name = (info_multi.get('toss_winner') or [''])[0]
        toss_winner_obj = None
        if toss_winner_name:
            toss_winner_obj = Team.objects.filter(name__iexact=toss_winner_name).first()

        toss_decision = (info_multi.get('toss_decision') or [''])[-1][:10]

        result_bits = []
        if winner_name:
            result_bits.append(f'{winner_name} won')
        if info_multi.get('winner_runs'):
            result_bits.append(f"by {info_multi['winner_runs'][0]} runs")
        if info_multi.get('winner_wickets'):
            result_bits.append(f"by {info_multi['winner_wickets'][0]} wickets")
        result_text = ' '.join(result_bits).strip()

        match_uid = f'cricsheet_{csv_path.stem}'
        match_name = f'{team1_name} vs {team2_name}'

        defaults = {
            'name': match_name,
            'team1': team1,
            'team2': team2,
            'venue': venue,
            'format': fmt,
            'category': category,
            'status': 'complete',
            'match_date': match_date,
            'winner': winner_obj,
            'toss_winner': toss_winner_obj,
            'toss_decision': toss_decision,
            'result_text': result_text,
            'raw_data': {
                'source': 'cricsheet_csv',
                'file': csv_path.name,
                'event': event_name,
                'season': (info_multi.get('season') or [''])[0],
            },
            'primary_source': 'cricsheet_csv',
            'confidence_score': 95,
            'source_urls': [{'provider': 'cricsheet_csv', 'file': csv_path.name}],
            'stats_completeness': 1.0 if innings_totals else 0.4,
        }
        match_obj, created = Match.objects.update_or_create(cricapi_id=match_uid, defaults=defaults)

        for innings_number, aggregate in innings_totals.items():
            batting_team_obj = Team.objects.filter(name__iexact=aggregate.batting_team).first()
            overs = round(aggregate.legal_balls / 6.0, 2)
            rr = round((aggregate.total_runs / overs), 2) if overs > 0 else 0.0
            MatchScorecard.objects.update_or_create(
                match=match_obj,
                innings_number=innings_number,
                defaults={
                    'batting_team': batting_team_obj,
                    'total_runs': aggregate.total_runs,
                    'total_wickets': aggregate.wickets,
                    'total_overs': overs,
                    'run_rate': rr,
                    'batting_data': [],
                    'bowling_data': [],
                },
            )

        for team_name, player_names in players_by_team.items():
            team_obj = Team.objects.filter(name__iexact=team_name).first()
            for player_name in player_names:
                Player.objects.update_or_create(
                    name=player_name,
                    defaults={
                        'full_name': player_name,
                        'team': team_obj,
                        'primary_source': 'cricsheet_csv',
                        'confidence_score': 88,
                        'source_urls': [{'provider': 'cricsheet_csv'}],
                    },
                )

        for (innings_number, player_name), bat in batting_stats.items():
            player_obj = Player.objects.filter(name__iexact=player_name).first()
            if not player_obj:
                continue
            stats_obj, _ = PlayerMatchStats.objects.get_or_create(
                player=player_obj,
                match=match_obj,
                innings_number=innings_number,
            )
            stats_obj.runs_scored = bat['runs']
            stats_obj.balls_faced = bat['balls']
            stats_obj.fours = bat['fours']
            stats_obj.sixes = bat['sixes']
            stats_obj.dismissed = bool(bat['dismissed'])
            stats_obj.strike_rate = round((bat['runs'] * 100.0 / bat['balls']), 2) if bat['balls'] else None

            bowl = bowling_stats.get((innings_number, player_name))
            if bowl:
                overs_bowled = round(float(bowl['legal_balls']) / 6.0, 2)
                stats_obj.overs_bowled = overs_bowled
                stats_obj.runs_conceded = int(bowl['runs_conceded'])
                stats_obj.wickets_taken = int(bowl['wickets'])
                stats_obj.economy = round((bowl['runs_conceded'] / overs_bowled), 2) if overs_bowled > 0 else None

            stats_obj.save()

        return created

    @transaction.atomic
    def _import_json_file(self, json_path: Path) -> bool:
        with json_path.open('r', encoding='utf-8') as handle:
            payload = json.load(handle)

        info = payload.get('info') or {}
        info_multi: dict[str, list[str]] = defaultdict(list)
        players_by_team: dict[str, set[str]] = defaultdict(set)

        for team_name in info.get('teams') or []:
            if team_name:
                info_multi['team'].append(str(team_name))

        if info.get('venue'):
            info_multi['venue'].append(str(info.get('venue')))
        if info.get('city'):
            info_multi['city'].append(str(info.get('city')))

        for dt in info.get('dates') or []:
            if dt:
                info_multi['date'].append(str(dt))

        event = info.get('event')
        if isinstance(event, dict):
            event_name = event.get('name')
            if event_name:
                info_multi['event'].append(str(event_name))
        elif event:
            info_multi['event'].append(str(event))

        if info.get('match_type'):
            info_multi['match_type'].append(str(info.get('match_type')))
        if info.get('season'):
            info_multi['season'].append(str(info.get('season')))

        toss = info.get('toss') or {}
        if toss.get('winner'):
            info_multi['toss_winner'].append(str(toss.get('winner')))
        if toss.get('decision'):
            info_multi['toss_decision'].append(str(toss.get('decision')))

        outcome = info.get('outcome') or {}
        if outcome.get('winner'):
            info_multi['winner'].append(str(outcome.get('winner')))
        by = outcome.get('by') or {}
        if by.get('runs') is not None:
            info_multi['winner_runs'].append(str(by.get('runs')))
        if by.get('wickets') is not None:
            info_multi['winner_wickets'].append(str(by.get('wickets')))

        players = info.get('players') or {}
        if isinstance(players, dict):
            for team_name, roster in players.items():
                if not isinstance(roster, list):
                    continue
                for player_name in roster:
                    if player_name:
                        players_by_team[str(team_name)].add(str(player_name))

        innings_totals: dict[int, InningAggregate] = {}
        batting_stats: dict[tuple[int, str], dict[str, int]] = defaultdict(
            lambda: {'runs': 0, 'balls': 0, 'fours': 0, 'sixes': 0, 'dismissed': 0}
        )
        bowling_stats: dict[tuple[int, str], dict[str, float]] = defaultdict(
            lambda: {'legal_balls': 0.0, 'runs_conceded': 0.0, 'wickets': 0.0}
        )

        for innings_number, innings_entry in enumerate(payload.get('innings') or [], start=1):
            inning_data = innings_entry
            if isinstance(innings_entry, dict) and 'team' not in innings_entry:
                first_value = next(iter(innings_entry.values()), {})
                if isinstance(first_value, dict):
                    inning_data = first_value

            batting_team = str((inning_data or {}).get('team') or '')
            inning = InningAggregate(innings_number=innings_number, batting_team=batting_team)
            innings_totals[innings_number] = inning

            deliveries: list[dict[str, Any]] = []
            overs = (inning_data or {}).get('overs')
            if isinstance(overs, list):
                for over in overs:
                    for delivery in (over or {}).get('deliveries') or []:
                        if isinstance(delivery, dict):
                            deliveries.append(delivery)
            else:
                for delivery in (inning_data or {}).get('deliveries') or []:
                    if isinstance(delivery, dict):
                        if 'runs' in delivery:
                            deliveries.append(delivery)
                        elif len(delivery) == 1:
                            inner = next(iter(delivery.values()))
                            if isinstance(inner, dict):
                                deliveries.append(inner)

            for delivery in deliveries:
                striker = str(delivery.get('batter') or delivery.get('batsman') or '').strip()
                bowler = str(delivery.get('bowler') or '').strip()

                runs = delivery.get('runs') or {}
                if isinstance(runs, dict):
                    batter_runs = _to_int(runs.get('batter', runs.get('batsman', 0)))
                    total_runs = _to_int(runs.get('total', 0))
                else:
                    batter_runs = _to_int(runs)
                    total_runs = batter_runs

                extras_obj = delivery.get('extras') or {}
                if isinstance(extras_obj, dict):
                    wide = _to_int(extras_obj.get('wides', extras_obj.get('wide', 0)))
                    no_ball = _to_int(
                        extras_obj.get('noballs', extras_obj.get('no_balls', extras_obj.get('no_ball', 0)))
                    )
                else:
                    wide = 0
                    no_ball = 0

                is_legal = wide == 0 and no_ball == 0

                wickets = delivery.get('wickets') or []
                if not isinstance(wickets, list):
                    wickets = []
                single_wicket = delivery.get('wicket')
                if isinstance(single_wicket, dict):
                    wickets = [*wickets, single_wicket]

                inning.total_runs += total_runs
                if is_legal:
                    inning.legal_balls += 1
                if wickets:
                    inning.wickets += len(wickets)

                if striker:
                    key = (innings_number, striker)
                    batting_stats[key]['runs'] += batter_runs
                    if is_legal:
                        batting_stats[key]['balls'] += 1
                    if batter_runs == 4:
                        batting_stats[key]['fours'] += 1
                    if batter_runs == 6:
                        batting_stats[key]['sixes'] += 1

                if bowler:
                    key = (innings_number, bowler)
                    if is_legal:
                        bowling_stats[key]['legal_balls'] += 1
                    bowling_stats[key]['runs_conceded'] += total_runs

                for wicket in wickets:
                    wicket_kind = str((wicket or {}).get('kind') or '').strip().lower()
                    player_out = str((wicket or {}).get('player_out') or '').strip()

                    if striker and player_out and player_out == striker:
                        batting_stats[(innings_number, striker)]['dismissed'] = 1

                    if bowler and wicket_kind and wicket_kind not in LEGAL_EXTRAS_WICKET_EXCLUDE:
                        bowling_stats[(innings_number, bowler)]['wickets'] += 1

        teams = info_multi.get('team', [])
        if len(teams) < 2:
            raise ValueError('missing team entries')

        team1_name = teams[0]
        team2_name = teams[1]
        team1, _ = Team.objects.get_or_create(
            name=team1_name,
            defaults={
                'short_name': team1_name[:10].upper(),
                'country': team1_name,
                'is_international': True,
                'primary_source': 'cricsheet_json',
                'confidence_score': 92,
                'source_urls': [{'provider': 'cricsheet_json'}],
            },
        )
        team2, _ = Team.objects.get_or_create(
            name=team2_name,
            defaults={
                'short_name': team2_name[:10].upper(),
                'country': team2_name,
                'is_international': True,
                'primary_source': 'cricsheet_json',
                'confidence_score': 92,
                'source_urls': [{'provider': 'cricsheet_json'}],
            },
        )

        venue_name = (info_multi.get('venue') or ['Unknown venue'])[0]
        city_name = (info_multi.get('city') or [''])[0]
        venue, _ = Venue.objects.get_or_create(
            name=venue_name,
            defaults={'city': city_name, 'country': '', 'pitch_type': 'balanced'},
        )

        match_type = (info_multi.get('match_type') or [''])[0]
        event_name = (info_multi.get('event') or [''])[0]
        fmt = _normalize_format(match_type=match_type, event=event_name)
        category = _infer_category(event=event_name)
        match_date = _parse_date(info_multi.get('date', []))

        winner_name = (info_multi.get('winner') or [''])[0]
        winner_obj = None
        if winner_name:
            winner_obj = Team.objects.filter(name__iexact=winner_name).first()

        toss_winner_name = (info_multi.get('toss_winner') or [''])[0]
        toss_winner_obj = None
        if toss_winner_name:
            toss_winner_obj = Team.objects.filter(name__iexact=toss_winner_name).first()

        toss_decision = (info_multi.get('toss_decision') or [''])[-1][:10]

        result_bits = []
        if winner_name:
            result_bits.append(f'{winner_name} won')
        if info_multi.get('winner_runs'):
            result_bits.append(f"by {info_multi['winner_runs'][0]} runs")
        if info_multi.get('winner_wickets'):
            result_bits.append(f"by {info_multi['winner_wickets'][0]} wickets")
        result_text = ' '.join(result_bits).strip()

        match_uid = f'cricsheet_{json_path.stem}'
        match_name = f'{team1_name} vs {team2_name}'

        defaults = {
            'name': match_name,
            'team1': team1,
            'team2': team2,
            'venue': venue,
            'format': fmt,
            'category': category,
            'status': 'complete',
            'match_date': match_date,
            'winner': winner_obj,
            'toss_winner': toss_winner_obj,
            'toss_decision': toss_decision,
            'result_text': result_text,
            'raw_data': {
                'source': 'cricsheet_json',
                'file': json_path.name,
                'event': event_name,
                'season': (info_multi.get('season') or [''])[0],
            },
            'primary_source': 'cricsheet_json',
            'confidence_score': 95,
            'source_urls': [{'provider': 'cricsheet_json', 'file': json_path.name}],
            'stats_completeness': 1.0 if innings_totals else 0.4,
        }
        match_obj, created = Match.objects.update_or_create(cricapi_id=match_uid, defaults=defaults)

        for innings_number, aggregate in innings_totals.items():
            batting_team_obj = Team.objects.filter(name__iexact=aggregate.batting_team).first()
            overs = round(aggregate.legal_balls / 6.0, 2)
            rr = round((aggregate.total_runs / overs), 2) if overs > 0 else 0.0
            MatchScorecard.objects.update_or_create(
                match=match_obj,
                innings_number=innings_number,
                defaults={
                    'batting_team': batting_team_obj,
                    'total_runs': aggregate.total_runs,
                    'total_wickets': aggregate.wickets,
                    'total_overs': overs,
                    'run_rate': rr,
                    'batting_data': [],
                    'bowling_data': [],
                },
            )

        for team_name, player_names in players_by_team.items():
            team_obj = Team.objects.filter(name__iexact=team_name).first()
            for player_name in player_names:
                Player.objects.update_or_create(
                    name=player_name,
                    defaults={
                        'full_name': player_name,
                        'team': team_obj,
                        'primary_source': 'cricsheet_json',
                        'confidence_score': 88,
                        'source_urls': [{'provider': 'cricsheet_json'}],
                    },
                )

        for (innings_number, player_name), bat in batting_stats.items():
            player_obj = Player.objects.filter(name__iexact=player_name).first()
            if not player_obj:
                continue

            stats_obj, _ = PlayerMatchStats.objects.get_or_create(
                player=player_obj,
                match=match_obj,
                innings_number=innings_number,
            )
            stats_obj.runs_scored = bat['runs']
            stats_obj.balls_faced = bat['balls']
            stats_obj.fours = bat['fours']
            stats_obj.sixes = bat['sixes']
            stats_obj.dismissed = bool(bat['dismissed'])
            stats_obj.strike_rate = round((bat['runs'] * 100.0 / bat['balls']), 2) if bat['balls'] else None

            bowl = bowling_stats.get((innings_number, player_name))
            if bowl:
                overs_bowled = round(float(bowl['legal_balls']) / 6.0, 2)
                stats_obj.overs_bowled = overs_bowled
                stats_obj.runs_conceded = int(bowl['runs_conceded'])
                stats_obj.wickets_taken = int(bowl['wickets'])
                stats_obj.economy = round((bowl['runs_conceded'] / overs_bowled), 2) if overs_bowled > 0 else None

            stats_obj.save()

        return created
