from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


def _check_database() -> str:
	try:
		with connection.cursor() as cursor:
			cursor.execute('SELECT 1')
			cursor.fetchone()
		return 'ok'
	except Exception:
		return 'error'


def _check_redis() -> str:
	try:
		cache.set('health:ping', 'pong', timeout=10)
		return 'ok' if cache.get('health:ping') == 'pong' else 'error'
	except Exception:
		return 'error'


def _check_celery() -> str:
	try:
		from config.celery import app as celery_app

		inspect = celery_app.control.inspect(timeout=1)
		ping = inspect.ping() if inspect else None
		return 'ok' if ping else 'unavailable'
	except Exception:
		return 'error'


def _has_model_artifact() -> bool:
	artifact_path = Path(settings.ML_MODEL_PATH)
	if not artifact_path.exists() or not artifact_path.is_dir():
		return False
	return any(file.suffix == '.joblib' for file in artifact_path.iterdir() if file.is_file())


class HealthView(APIView):
	permission_classes = [AllowAny]

	def get(self, request):
		payload = {
			'status': 'ok',
			'db': _check_database(),
			'redis': _check_redis(),
			'celery': _check_celery(),
		}
		return Response(payload)


class ReadyView(APIView):
	permission_classes = [AllowAny]

	def get(self, request):
		db_status = _check_database()
		redis_status = _check_redis()
		model_artifact = _has_model_artifact()
		ready = db_status == 'ok' and redis_status == 'ok' and model_artifact
		payload = {
			'status': 'ready' if ready else 'not_ready',
			'db': db_status,
			'redis': redis_status,
			'model_artifact': 'ok' if model_artifact else 'missing',
		}
		status_code = 200 if ready else 503
		return Response(payload, status=status_code)
