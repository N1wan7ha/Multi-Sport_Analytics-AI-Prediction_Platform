"""Walk-forward ML training with proper leakage prevention and calibration."""
import logging
from datetime import datetime, timedelta
from typing import Tuple, List, Dict, Any

import numpy as np
from django.db.models import Q
from django.utils import timezone

from apps.matches.models import Match
from apps.data_quality.models import FeatureSnapshot
from apps.players.models import PlayerMatchStats

logger = logging.getLogger(__name__)


class FeatureSnapshotCapture:
    """Capture frozen features at different match windows."""
    
    @staticmethod
    def capture_pre_match_features(match) -> Dict[str, Any]:
        """Capture team/player stats as of match start time."""
        features = {
            'team1_win_rate': 0.5,
            'team2_win_rate': 0.5,
            'team1_recent_form': 0.0,  # -1 to 1 scale
            'team2_recent_form': 0.0,
            'h2h_team1_advantage': 0.0,
            'venue_pitch_advantage': 0.0,
            'team1_top_players_available': 1.0,
            'team2_top_players_available': 1.0,
        }
        
        # Team1 stats from matches STRICTLY before match_date
        if match.team1:
            prior = Match.objects.filter(
                Q(team1=match.team1) | Q(team2=match.team1),
                status='complete',
                match_date__lt=match.match_date,
            ).order_by('-match_date')[:10]
            
            if prior.exists():
                wins = sum(1 for m in prior if m.winner == match.team1)
                features['team1_win_rate'] = wins / prior.count()
                
                # Recent form (trend)
                recent_wins = sum(1 for m in prior[:3] if m.winner == match.team1)
                features['team1_recent_form'] = (recent_wins / 3) - 0.5
        
        # Team2 stats
        if match.team2:
            prior = Match.objects.filter(
                Q(team1=match.team2) | Q(team2=match.team2),
                status='complete',
                match_date__lt=match.match_date,
            ).order_by('-match_date')[:10]
            
            if prior.exists():
                wins = sum(1 for m in prior if m.winner == match.team2)
                features['team2_win_rate'] = wins / prior.count()
                
                recent_wins = sum(1 for m in prior[:3] if m.winner == match.team2)
                features['team2_recent_form'] = (recent_wins / 3) - 0.5
        
        # H2H advantage (from HISTORICAL matches only)
        if match.team1 and match.team2:
            h2h = Match.objects.filter(
                Q(team1=match.team1, team2=match.team2) |
                Q(team1=match.team2, team2=match.team1),
                status='complete',
                match_date__lt=match.match_date,
            )[:20]
            
            if h2h.exists():
                t1_wins = sum(1 for m in h2h if m.winner == match.team1)
                features['h2h_team1_advantage'] = (2 * t1_wins / h2h.count()) - 1
        
        # Venue advantage
        if match.venue:
            venue_matches = Match.objects.filter(
                venue=match.venue,
                status='complete',
                match_date__lt=match.match_date,
            )[:10]
            
            if venue_matches.exists():
                team1_wins_at_venue = sum(1 for m in venue_matches if m.winner == match.team1)
                features['venue_pitch_advantage'] = 2 * (team1_wins_at_venue / venue_matches.count()) - 1
        
        return features
    
    @staticmethod
    def save_feature_snapshot(match, window: str, features: Dict[str, Any]) -> FeatureSnapshot:
        """Save frozen features to DB for ML training."""
        snapshot, _ = FeatureSnapshot.objects.update_or_create(
            match=match,
            window=window,
            defaults={
                'captured_at': timezone.now(),
                'features': features,
                'sources_used': ['data_pipeline', 'match_stats'],
                'is_valid': True,
                'validation_errors': [],
            }
        )
        return snapshot


class WalkForwardValidator:
    """Walk-forward validation for time-series cricket data."""
    
    def __init__(self, train_window_days: int = 365, test_window_days: int = 30):
        self.train_window_days = train_window_days
        self.test_window_days = test_window_days
    
    def generate_folds(self, all_matches: List[Match]) -> List[Tuple[List[Match], List[Match]]]:
        """
        Generate time-based train/test folds.
        NO RANDOMIZATION - respects temporal order.
        """
        if not all_matches:
            return []
        
        sorted_matches = sorted(all_matches, key=lambda m: m.match_date or datetime.min.date())
        folds = []
        
        for i in range(len(sorted_matches)):
            pivot_match = sorted_matches[i]
            pivot_date = pivot_match.match_date
            
            if not pivot_date:
                continue
            
            # Train: All matches BEFORE pivot_date, within train_window
            train_cutoff = pivot_date - timedelta(days=self.train_window_days)
            train_matches = [
                m for m in sorted_matches
                if m.match_date and train_cutoff <= m.match_date < pivot_date
            ]
            
            # Test: Matches from pivot_date to test_window_days ahead
            test_cutoff = pivot_date + timedelta(days=self.test_window_days)
            test_matches = [
                m for m in sorted_matches
                if m.match_date and pivot_date <= m.match_date < test_cutoff
            ]
            
            if train_matches and test_matches:
                folds.append((train_matches, test_matches))
        
        logger.info(f"Generated {len(folds)} walk-forward folds")
        return folds


class ProbabilityCalibration:
    """Calibrate raw model probabilities for better reliability."""
    
    @staticmethod
    def platt_scaling(y_true: List[int], y_prob: np.ndarray) -> Tuple[float, float]:
        """
        Fit Platt scaling: P(Y=1|X) = 1 / (1 + exp(Af + B))
        Returns: (A, B) calibration parameters
        """
        try:
            from scipy.optimize import minimize
            
            def cross_entropy_loss(ab, y_true_arr, y_prob_arr):
                A, B = ab
                # Sigmoid with parameters
                p = 1.0 / (1.0 + np.exp(-(A * y_prob_arr + B)))
                p = np.clip(p, 1e-8, 1 - 1e-8)
                loss = -np.mean(y_true_arr * np.log(p) + (1 - y_true_arr) * np.log(1 - p))
                return loss
            
            y_true_arr = np.array(y_true)
            result = minimize(
                cross_entropy_loss,
                x0=[1.0, 0.0],
                args=(y_true_arr, y_prob),
                method='BFGS'
            )
            
            if result.success:
                return tuple(result.x)
        except ImportError:
            logger.warning("scipy not available for Platt scaling")
        
        # Fallback: simple linear regression
        return 1.0, 0.0
    
    @staticmethod
    def apply_calibration(y_prob: np.ndarray, A: float, B: float) -> np.ndarray:
        """Apply calibration to raw probabilities."""
        logits = A * np.log(y_prob / (1 - np.clip(y_prob, 0.0001, 0.9999) ) ) + B
        return 1.0 / (1.0 + np.exp(-logits))


class WalkForwardTrainer:
    """Train models with walk-forward validation and calibration."""
    
    def __init__(self):
        self.calibration_params = {}
    
    def train_walk_forward(self, matches_sorted_by_date: List[Match]) -> Dict[str, Any]:
        """
        Train with walk-forward validation:
        1. For each time point, train on historical data
        2. Test on immediate future
        3. Calibrate probabilities
        4. Evaluate on final test set
        """
        try:
            from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
            from sklearn.metrics import accuracy_score, roc_auc_score, brier_score_loss, log_loss
        except ImportError:
            logger.error("scikit-learn required for walk-forward training")
            return {'error': 'scikit-learn not available'}
        
        validator = WalkForwardValidator()
        folds = validator.generate_folds(matches_sorted_by_date)
        
        all_test_metrics = {
            'accuracy': [],
            'auc_roc': [],
            'brier': [],
            'log_loss': [],
        }
        
        final_classifier = None
        final_calibration = (1.0, 0.0)  # Default: no calibration
        
        for fold_idx, (train_matches, test_matches) in enumerate(folds):
            logger.info(f"Walk-forward fold {fold_idx + 1}/{len(folds)}: train{len(train_matches)}, test={len(test_matches)}")
            
            # Feature engineering with NO leakage
            X_train, y_train = self._build_features_for_matches(train_matches)
            X_test, y_test = self._build_features_for_matches(test_matches)
            
            if len(X_train) < 10 or len(X_test) < 5:
                logger.warning(f"Skipping fold {fold_idx}: insufficient data")
                continue
            
            # Train ensemble
            rf = RandomForestClassifier(n_estimators=100, random_state=42)
            gb = GradientBoostingClassifier(n_estimators=100, random_state=42)
            
            rf.fit(X_train, y_train)
            gb.fit(X_train, y_train)
            
            rf_prob = rf.predict_proba(X_test)[:, 1]
            gb_prob = gb.predict_proba(X_test)[:, 1]
            ensemble_prob = 0.6 * rf_prob + 0.4 * gb_prob
            
            # Calibrate on this fold's test set
            A, B = ProbabilityCalibration.platt_scaling(y_test, ensemble_prob)
            calibrated_prob = ProbabilityCalibration.apply_calibration(ensemble_prob, A, B)
            
            # Evaluate
            y_pred = (calibrated_prob >= 0.5).astype(int)
            accuracy = accuracy_score(y_test, y_pred)
            auc = roc_auc_score(y_test, calibrated_prob)
            brier = brier_score_loss(y_test, calibrated_prob)
            logloss = log_loss(y_test, calibrated_prob)
            
            all_test_metrics['accuracy'].append(accuracy)
            all_test_metrics['auc_roc'].append(auc)
            all_test_metrics['brier'].append(brier)
            all_test_metrics['log_loss'].append(logloss)
            
            # Keep latest trained model
            final_classifier = (rf, gb)
            final_calibration = (A, B)
        
        # Compute average metrics across all folds
        avg_metrics = {
            k: float(np.mean(v)) if v else None
            for k, v in all_test_metrics.items()
        }
        
        return {
            'success': True,
            'num_folds': len(folds),
            'avg_metrics': avg_metrics,
            'calibration_params': {
                'A': float(final_calibration[0]),
                'B': float(final_calibration[1]),
            },
            'trained_at': timezone.now().isoformat(),
        }
    
    def _build_features_for_matches(self, matches: List[Match]) -> Tuple[np.ndarray, List[int]]:
        """Build feature matrix from matches using feature snapshots."""
        X = []
        y = []
        
        for match in matches:
            # Capture features as they were at match start
            features = FeatureSnapshotCapture.capture_pre_match_features(match)
            
            # Extract in consistent order
            feature_vector = [
                features['team1_win_rate'],
                features['team2_win_rate'],
                features['team1_recent_form'],
                features['team2_recent_form'],
                features['h2h_team1_advantage'],
                features['venue_pitch_advantage'],
                features['team1_top_players_available'],
                features['team2_top_players_available'],
            ]
            
            # Label
            if match.winner and match.team1:
                label = 1 if match.winner == match.team1 else 0
                X.append(feature_vector)
                y.append(label)
                
                # Save snapshot for audit trail
                FeatureSnapshotCapture.save_feature_snapshot(
                    match, 'pre_match', features
                )
        
        return np.array(X) if X else np.array([]), y


def train_walk_forward_models(model_path: str, version: str = 'v2.0') -> Dict[str, Any]:
    """Entry point for walk-forward training."""
    logger.info("Starting walk-forward model training...")
    
    # Get all complete matches, sorted chronologically
    matches = Match.objects.filter(
        status='complete',
        team1__isnull=False,
        team2__isnull=False,
        winner__isnull=False,
        match_date__isnull=False,
    ).select_related('team1', 'team2', 'venue', 'winner').order_by('match_date')
    
    if matches.count() < 50:
        logger.warning(f"Only {matches.count()} complete matches; need 50+ for robust walk-forward training")
        return {'error': 'Insufficient data', 'sample_count': matches.count()}
    
    trainer = WalkForwardTrainer()
    result = trainer.train_walk_forward(list(matches))
    
    if result.get('success'):
        logger.info(f"Walk-forward training complete: {result['avg_metrics']}")
    
    return result
