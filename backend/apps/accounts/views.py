import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.mail import send_mail
from django.db import models
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import generics
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.matches.models import Team
from apps.players.models import Player
from apps.predictions.models import PredictionJob
from .models import UserFavouritePlayer, UserFavouriteTeam
from .serializers import CustomTokenObtainPairSerializer

User = get_user_model()
logger = logging.getLogger(__name__)


class TeamMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'short_name', 'logo_url']


class PlayerMiniSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = Player
        fields = ['id', 'name', 'full_name', 'team_name', 'country', 'image_url']


class PredictionResultMiniSerializer(serializers.Serializer):
    team1_win_probability = serializers.FloatField()
    team2_win_probability = serializers.FloatField()
    confidence_score = serializers.FloatField()
    current_over = serializers.IntegerField(allow_null=True)
    current_score = serializers.CharField(allow_blank=True)


class PredictionHistorySerializer(serializers.ModelSerializer):
    result = serializers.SerializerMethodField()
    match_name = serializers.CharField(source='match.name', read_only=True)

    class Meta:
        model = PredictionJob
        fields = [
            'id', 'match', 'match_name', 'prediction_type', 'status', 'model_version',
            'requested_at', 'completed_at', 'result',
        ]

    def get_result(self, obj):
        if not hasattr(obj, 'result'):
            return None
        return PredictionResultMiniSerializer(obj.result).data


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    favourite_team_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        write_only=True,
    )
    favourite_player_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        required=False,
        write_only=True,
    )
    favourite_teams = serializers.SerializerMethodField(read_only=True)
    favourite_players = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'password', 'role', 'email_verified', 'bio',
            'favourite_team', 'favourite_team_ids', 'favourite_player_ids', 'favourite_teams', 'favourite_players',
        ]
        read_only_fields = ['role', 'email_verified']

    def validate_favourite_team_ids(self, value):
        if len(value) > 5:
            raise serializers.ValidationError('You can select up to 5 favourite teams.')
        if len(set(value)) != len(value):
            raise serializers.ValidationError('Duplicate favourite teams are not allowed.')
        return value

    def validate_favourite_player_ids(self, value):
        if len(value) > 11:
            raise serializers.ValidationError('You can select up to 11 favourite players.')
        if len(set(value)) != len(value):
            raise serializers.ValidationError('Duplicate favourite players are not allowed.')
        return value

    def create(self, validated_data):
        validated_data.pop('favourite_team_ids', None)
        validated_data.pop('favourite_player_ids', None)
        return User.objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        favourite_team_ids = validated_data.pop('favourite_team_ids', None)
        favourite_player_ids = validated_data.pop('favourite_player_ids', None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()

        if favourite_team_ids is not None:
            teams = Team.objects.filter(id__in=favourite_team_ids)
            UserFavouriteTeam.objects.filter(user=instance).exclude(team__in=teams).delete()
            existing_team_ids = set(
                UserFavouriteTeam.objects.filter(user=instance).values_list('team_id', flat=True)
            )
            for team in teams:
                if team.id not in existing_team_ids:
                    UserFavouriteTeam.objects.create(user=instance, team=team)

        if favourite_player_ids is not None:
            players = Player.objects.filter(id__in=favourite_player_ids)
            UserFavouritePlayer.objects.filter(user=instance).exclude(player__in=players).delete()
            existing_player_ids = set(
                UserFavouritePlayer.objects.filter(user=instance).values_list('player_id', flat=True)
            )
            for player in players:
                if player.id not in existing_player_ids:
                    UserFavouritePlayer.objects.create(user=instance, player=player)

        return instance

    def get_favourite_teams(self, obj):
        teams = Team.objects.filter(favoured_by_users__user=obj).order_by('name')
        return TeamMiniSerializer(teams, many=True).data

    def get_favourite_players(self, obj):
        players = Player.objects.filter(favoured_by_users__user=obj).select_related('team').order_by('name')
        return PlayerMiniSerializer(players, many=True).data


class GoogleAuthSerializer(serializers.Serializer):
    token = serializers.CharField()


class EmailVerificationConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate_current_password(self, value):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value


def _generate_unique_username(base: str) -> str:
    sanitized = ''.join(ch for ch in base if ch.isalnum() or ch in {'_', '.'}).strip('._')
    base_username = (sanitized or 'user')[:30]
    candidate = base_username
    suffix = 1

    while User.objects.filter(username=candidate).exists():
        suffix_part = f'_{suffix}'
        candidate = f"{base_username[: max(1, 30 - len(suffix_part))]}{suffix_part}"
        suffix += 1

    return candidate


def _build_verification_link(token: str) -> str:
    base = getattr(settings, 'FRONTEND_URL', 'http://localhost:4200').rstrip('/')
    return f'{base}/auth/verify-email?token={token}'


def _send_verification_email(user: User) -> None:
    token = signing.dumps({'user_id': user.id, 'email': user.email}, salt='accounts-email-verify')
    verification_link = _build_verification_link(token)
    send_mail(
        subject='Verify your MatchMind email',
        message=(
            f'Hi {user.username},\n\n'
            f'Please verify your email by visiting this link:\n{verification_link}\n\n'
            'If you did not create this account, please ignore this email.'
        ),
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        recipient_list=[user.email],
        fail_silently=False,
    )

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = []

    def perform_create(self, serializer):
        user = serializer.save()
        try:
            _send_verification_email(user)
        except Exception:
            logger.exception('Failed to send verification email for user_id=%s', user.id)


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class GoogleAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
        if not client_id:
            return Response({'detail': 'Google OAuth is not configured'}, status=503)

        token = serializer.validated_data['token']

        try:
            idinfo = google_id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                client_id,
            )
        except Exception:
            return Response({'detail': 'Invalid Google token'}, status=400)

        email = idinfo.get('email')
        if not email:
            return Response({'detail': 'Google account email is missing'}, status=400)

        email_verified = bool(idinfo.get('email_verified', False))
        if not email_verified:
            return Response({'detail': 'Google email is not verified'}, status=400)

        user = User.objects.filter(email=email).first()
        if user is None:
            preferred_username = idinfo.get('name') or email.split('@')[0]
            user = User.objects.create_user(
                email=email,
                username=_generate_unique_username(preferred_username),
                password=None,
                email_verified=True,
            )
            user.set_unusable_password()
            user.save(update_fields=['password'])
        elif not user.email_verified:
            user.email_verified = True
            user.save(update_fields=['email_verified'])

        if not user.is_active:
            return Response({'detail': 'User account is disabled'}, status=403)

        refresh = CustomTokenObtainPairSerializer.get_token(user)
        return Response(
            {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        )


class ResendEmailVerificationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.email_verified:
            return Response({'detail': 'Email is already verified'})

        _send_verification_email(user)
        return Response({'detail': 'Verification email sent'})


class ConfirmEmailVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payload = signing.loads(
                serializer.validated_data['token'],
                salt='accounts-email-verify',
                max_age=getattr(settings, 'EMAIL_VERIFICATION_TOKEN_MAX_AGE', 86400),
            )
        except signing.SignatureExpired:
            return Response({'detail': 'Verification token expired'}, status=400)
        except signing.BadSignature:
            return Response({'detail': 'Invalid verification token'}, status=400)

        user_id = payload.get('user_id')
        email = payload.get('email')
        user = User.objects.filter(id=user_id, email=email).first()
        if user is None:
            return Response({'detail': 'User not found for token'}, status=404)

        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=['email_verified'])

        return Response({'detail': 'Email verified successfully'})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])

        return Response({'detail': 'Password updated successfully.'})

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class TeamOptionsView(generics.ListAPIView):
    serializer_class = TeamMiniSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        queryset = Team.objects.order_by('name')
        query = (self.request.query_params.get('q') or '').strip()
        if query:
            queryset = queryset.filter(
                models.Q(name__icontains=query)
                | models.Q(short_name__icontains=query)
                | models.Q(country__icontains=query)
            )
        return queryset


class PlayerOptionsView(generics.ListAPIView):
    serializer_class = PlayerMiniSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        queryset = Player.objects.select_related('team').order_by('name')
        query = (self.request.query_params.get('q') or '').strip()
        if query:
            queryset = queryset.filter(
                models.Q(name__icontains=query)
                | models.Q(full_name__icontains=query)
                | models.Q(team__name__icontains=query)
                | models.Q(country__icontains=query)
            )
        return queryset[:250]


class PredictionHistoryView(generics.ListAPIView):
    serializer_class = PredictionHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PredictionJob.objects.filter(
            requested_by=self.request.user
        ).select_related('result').order_by('-requested_at')
