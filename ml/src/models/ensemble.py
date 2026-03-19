"""
ML Ensemble Predictor — Cricket Analytics Platform

Loads trained models from artifacts/ and returns pre-match win probabilities.
"""
import os
import logging
import numpy as np

logger = logging.getLogger(__name__)

# Lazy-loaded model instances
_models = {}


def _load_models(model_path: str, version: str):
    """Load pre-trained model artifacts (lazy, cached in memory)."""
    global _models
    if version in _models:
        return _models[version]

    try:
        import joblib
        models = {
            'rf': joblib.load(os.path.join(model_path, version, 'random_forest.pkl')),
            'xgb': joblib.load(os.path.join(model_path, version, 'xgboost.pkl')),
        }
        _models[version] = models
        logger.info(f"Loaded ML models version {version}")
        return models
    except FileNotFoundError:
        logger.warning(f"Models not found at {model_path}/{version}. Using dummy predictor.")
        return None


def predict_pre_match(features_array: np.ndarray, model_path: str, version: str = 'v1.0') -> dict:
    """
    Run ensemble prediction on pre-match features.

    Returns:
        dict with team1_win_prob, team2_win_prob, confidence_score
    """
    models = _load_models(model_path, version)

    if models is None:
        # Dummy predictor while models are being trained
        logger.warning("Using dummy predictor — train models first!")
        team1_prob = float(np.clip(np.random.normal(0.5, 0.15), 0.1, 0.9))
        return {
            'team1_win_probability': round(team1_prob, 4),
            'team2_win_probability': round(1 - team1_prob, 4),
            'confidence_score': 0.30,  # Low confidence for dummy
            'model_version': version,
            'is_dummy': True,
        }

    # Ensemble predictions
    weights = {'rf': 0.30, 'xgb': 0.35}  # Phase 3: add neural net (0.25) + meta (0.10)

    team1_probs = []
    for name, model in models.items():
        prob = model.predict_proba(features_array)[0][1]  # P(team1 wins)
        team1_probs.append((prob, weights[name]))

    # Weighted average
    total_weight = sum(w for _, w in team1_probs)
    team1_prob = sum(p * w for p, w in team1_probs) / total_weight
    team1_prob = float(np.clip(team1_prob, 0.05, 0.95))

    # Confidence: deviation from 0.5 (how decisive the prediction is)
    confidence = min(abs(team1_prob - 0.5) * 2 + 0.3, 1.0)

    return {
        'team1_win_probability': round(team1_prob, 4),
        'team2_win_probability': round(1 - team1_prob, 4),
        'confidence_score': round(confidence, 4),
        'model_version': version,
        'is_dummy': False,
    }
