from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound

from apps.matches.models import Match
from .models import PredictionJob, PredictionResult
from .tasks import process_prediction_job


class PredictionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = PredictionResult
        fields = [
            'team1', 'team2',
            'team1_win_probability', 'team2_win_probability', 'draw_probability',
            'confidence_score', 'key_factors', 'feature_snapshot',
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

    def create(self, validated_data):
        request = self.context['request']
        job = PredictionJob.objects.create(
            match=validated_data['match'],
            prediction_type=validated_data.get('prediction_type', 'pre_match'),
            status='pending',
            requested_by=request.user,
        )

        # In dev, Celery eager mode executes this immediately; in prod it is async.
        task_result = process_prediction_job.delay(job.id)
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
        job = PredictionJob.objects.select_related('result').filter(
            match_id=match_id,
            status='complete',
        ).order_by('-requested_at').first()
        if not job:
            raise NotFound('No prediction available yet.')
        return Response(PredictionJobSerializer(job).data)
