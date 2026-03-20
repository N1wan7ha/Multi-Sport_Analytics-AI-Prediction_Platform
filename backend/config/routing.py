"""ASGI websocket routing configuration."""

from django.urls import path

from apps.predictions.consumers import LivePredictionConsumer

websocket_urlpatterns = [
	path('ws/predictions/match/<int:match_id>/', LivePredictionConsumer.as_asgi()),
]