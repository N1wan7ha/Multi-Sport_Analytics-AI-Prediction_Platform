"""
ML train script — Phase 3 placeholder.
Run this script to train the pre-match ensemble model.

Usage:
  cd ml
  python src/models/train.py

Will be filled out in Phase 3 with:
- Load match data via data_loader
- Feature engineering via pre_match.py
- Train RF + XGBoost + Neural Net
- Cross-validate and log metrics
- Save model artifacts
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

# Bootstrap Django
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'backend')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

from src.utils.data_loader import setup_django, load_matches_df

setup_django()


def train():
    logger.info("Loading match data...")
    df = load_matches_df()

    if df.empty:
        logger.warning(
            "No completed matches in DB yet. Run 'python manage.py sync_matches' first, "
            "then populate the DB by running the data pipeline (Phase 1)."
        )
        return

    logger.info(f"Loaded {len(df)} completed matches")

    # ── Phase 3: implement full training pipeline ──────────
    # from src.features.pre_match import build_pre_match_features
    # from src.utils.preprocessor import encode_features, build_feature_matrix, scale_features
    # import sklearn, xgboost ...
    # ...

    logger.info("Training placeholder complete. Implement full pipeline in Phase 3.")


if __name__ == '__main__':
    train()
