from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.matches.models import Team, Venue, Match
import random


class Command(BaseCommand):
    help = 'Seed test database with completed matches for ML training'

    def handle(self, *args, **options):
        # Teams to use
        teams_list = [
            ('India', 'IND'), ('Australia', 'AUS'), ('England', 'ENG'),
            ('Pakistan', 'PAK'), ('Sri Lanka', 'SL'), ('New Zealand', 'NZ'),
            ('South Africa', 'SA'), ('West Indies', 'WI'), ('Bangladesh', 'BD'),
            ('Afghanistan', 'AFG'),
        ]

        # Venues
        venues_list = [
            ('MCG', 'Melbourne', 'batting'), ('Sydney Cricket Ground', 'Sydney', 'batting'),
            ('Eden Gardens', 'Kolkata', 'balanced'), ('Lord\'s', 'London', 'balanced'),
            ('Gaddafi Stadium', 'Lahore', 'bowling'), ('R. Premadasa Stadium', 'Colombo', 'bowling'),
        ]

        # Create venues
        venues = []
        for venue_name, city, pitch_type in venues_list:
            venue, _ = Venue.objects.get_or_create(
                name=venue_name,
                defaults={'city': city, 'country': 'Multiple', 'pitch_type': pitch_type}
            )
            venues.append(venue)

        # Create teams
        teams = {}
        for team_name, code in teams_list:
            team, _ = Team.objects.get_or_create(
                name=team_name,
                defaults={
                    'short_name': code,
                    'country': team_name,
                    'is_international': True,
                }
            )
            teams[team_name] = team

        # Create 30 completed matches
        base_date = timezone.now() - timedelta(days=60)
        formats = ['ODI', 'T20I', 'Test']
        categories = ['International', 'Bilateral', 'Tournament']

        match_count = 0
        team_names = list(teams.keys())

        for i in range(30):
            # Pick two different teams
            team1_name, team2_name = random.sample(team_names, 2)
            team1 = teams[team1_name]
            team2 = teams[team2_name]
            winner = random.choice([team1, team2])  # Random winner
            
            match_date = base_date + timedelta(days=i*2)
            format_type = random.choice(formats)
            match_name = f"{team1_name} vs {team2_name} - {format_type}"
            
            match, created = Match.objects.get_or_create(
                cricapi_id=f'test_cricapi_{i}',
                defaults={
                    'name': match_name,
                    'team1': team1,
                    'team2': team2,
                    'winner': winner,
                    'match_date': match_date,
                    'format': format_type.lower(),
                    'category': random.choice(categories),
                    'status': 'complete',
                    'venue': random.choice(venues),
                }
            )
            if created:
                match_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {match_count} completed matches for training'
            )
        )
