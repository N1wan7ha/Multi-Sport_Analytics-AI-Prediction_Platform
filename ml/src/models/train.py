"""ML train script for pre-match models (Phase 3)."""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Bootstrap Django
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

from src.utils.data_loader import setup_django

# Reuse backend training implementation to keep serving/training logic in sync.
from ml_engine.training import train_models_from_matches
from django.conf import settings

setup_django()


def train():
    logger.info("Starting Phase 3 model training...")
    summary = train_models_from_matches(settings.ML_MODEL_PATH, version=settings.ML_MODEL_VERSION)
    logger.info(
        "Training complete | version=%s samples=%s model=%s accuracy=%s auc=%s brier=%s",
        summary.version,
        summary.sample_count,
        summary.model_type,
        summary.accuracy,
        summary.auc_roc,
        summary.brier_score,
    )


if __name__ == '__main__':
    train()
