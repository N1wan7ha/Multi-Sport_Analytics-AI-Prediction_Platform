from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound

from apps.matches.models import Match
from .models import PredictionJob, PredictionResult
from .tasks import process_prediction_job


class PredictionResultSerializer(serializers.ModelSerializer):
    explainability = serializers.SerializerMethodField()
    pre_match_projection = serializers.SerializerMethodField()
    team_strength_score = serializers.SerializerMethodField()
    player_impact_score = serializers.SerializerMethodField()
    momentum_score = serializers.SerializerMethodField()

    def get_explainability(self, obj):
        return ((obj.feature_snapshot or {}).get('explainability') or {})

    def get_pre_match_projection(self, obj):
        return ((obj.feature_snapshot or {}).get('pre_match_projection') or {})

    def get_team_strength_score(self, obj):
        return self.get_explainability(obj).get('team_strength_score')

    def get_player_impact_score(self, obj):
        return self.get_explainability(obj).get('player_impact_score')

    def get_momentum_score(self, obj):
        return self.get_explainability(obj).get('momentum_score')

    class Meta:
        model = PredictionResult
        fields = [
            'team1', 'team2',
            'team1_win_probability', 'team2_win_probability', 'draw_probability',
            'confidence_score', 'key_factors', 'feature_snapshot',
            'explainability', 'pre_match_projection',
            'team_strength_score', 'player_impact_score', 'momentum_score',
            'current_over', 'current_score', 'created_at',
        ]


class PredictionJobSerializer(serializers.ModelSerializer):
    result = PredictionResultSerializer(read_only=True)

    class Meta:
        model = PredictionJob
        fields = [
            'id', 'match', 'prediction_type', 'status', 'celery_task_id',
            'model_version', 'error_message', 'requested_at', 'completed_at', 'result',
        ]


class PredictionCreateSerializer(serializers.Serializer):
    match = serializers.PrimaryKeyRelatedField(queryset=Match.objects.all())
    prediction_type = serializers.ChoiceField(choices=PredictionJob.TYPE_CHOICES, default='pre_match')
    current_over = serializers.IntegerField(required=False, min_value=0)
    current_score = serializers.CharField(required=False, allow_blank=True, max_length=50)

    def validate(self, attrs):
        match = attrs.get('match')
        prediction_type = attrs.get('prediction_type', 'pre_match')

        if match and match.status not in {'upcoming', 'live'}:
            raise serializers.ValidationError(
                {'match': 'AI predictions are available only for upcoming or live matches.'}
            )

        if prediction_type == 'live' and match and match.status != 'live':
            raise serializers.ValidationError(
                {'prediction_type': 'Live prediction can only run for matches with live status.'}
            )

        return attrs

    def create(self, validated_data):
        request = self.context['request']
        job = PredictionJob.objects.create(
            match=validated_data['match'],
            prediction_type=validated_data.get('prediction_type', 'pre_match'),
            status='pending',
            requested_by=request.user,
        )

        # In dev, Celery eager mode executes this immediately; in prod it is async.
        task_result = process_prediction_job.delay(
            job.id,
            validated_data.get('current_over'),
            validated_data.get('current_score', ''),
        )
        job.celery_task_id = str(task_result.id)
        job.save(update_fields=['celery_task_id'])
        job.refresh_from_db()
        return job


class PredictionCreateView(generics.CreateAPIView):
    serializer_class = PredictionCreateSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        job = serializer.save()
        output = PredictionJobSerializer(job).data
        return Response(output, status=201)


class PredictionDetailView(generics.RetrieveAPIView):
    queryset = PredictionJob.objects.select_related('result').all()
    serializer_class = PredictionJobSerializer
    permission_classes = [IsAuthenticated]


class MatchLatestPredictionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, match_id):
        prediction_type = request.query_params.get('prediction_type')
        job = PredictionJob.objects.select_related('result').filter(
            match_id=match_id,
            status='complete',
        )
        if prediction_type in {'pre_match', 'live'}:
            job = job.filter(prediction_type=prediction_type)
        job = job.order_by('-requested_at').first()
        if not job:
            raise NotFound('No prediction available yet.')
        return Response(PredictionJobSerializer(job).data)
