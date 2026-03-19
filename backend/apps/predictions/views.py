from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from .models import PredictionJob, PredictionResult

class PredictionJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = PredictionJob
        fields = ['id', 'match', 'prediction_type', 'status', 'model_version', 'requested_at', 'completed_at']

class PredictionCreateView(generics.CreateAPIView):
    serializer_class = PredictionJobSerializer
    permission_classes = [IsAuthenticated]
    def perform_create(self, serializer):
        job = serializer.save(requested_by=self.request.user)
        # TODO Phase 3: trigger celery prediction task here

class PredictionDetailView(generics.RetrieveAPIView):
    queryset = PredictionJob.objects.all()
    serializer_class = PredictionJobSerializer
    permission_classes = [IsAuthenticated]

class MatchLatestPredictionView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, match_id):
        job = PredictionJob.objects.filter(match_id=match_id, status='complete').order_by('-requested_at').first()
        if not job:
            return Response({'detail': 'No prediction available yet.'}, status=404)
        return Response(PredictionJobSerializer(job).data)
