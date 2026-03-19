"""ML models evaluate.py — model accuracy + calibration metrics. Phase 3 placeholder."""
import numpy as np
from sklearn.metrics import (
    accuracy_score, roc_auc_score, brier_score_loss,
    classification_report, confusion_matrix
)


def evaluate_model(model, X_test: np.ndarray, y_test: np.ndarray) -> dict:
    """
    Evaluate a trained model against Phase 0 targets:
    - Accuracy >= 86%
    - AUC-ROC   >= 0.90
    - Brier     <  0.20
    """
    y_pred      = model.predict(X_test)
    y_pred_prob = model.predict_proba(X_test)[:, 1]

    metrics = {
        'accuracy':    round(accuracy_score(y_test, y_pred), 4),
        'auc_roc':     round(roc_auc_score(y_test, y_pred_prob), 4),
        'brier_score': round(brier_score_loss(y_test, y_pred_prob), 4),
    }

    print("\n── Model Evaluation Report ──────────────────")
    print(f"  Accuracy   : {metrics['accuracy']:.1%}  (target ≥ 86%)")
    print(f"  AUC-ROC    : {metrics['auc_roc']:.4f}  (target ≥ 0.90)")
    print(f"  Brier Score: {metrics['brier_score']:.4f} (target < 0.20)")
    print("\n" + classification_report(y_test, y_pred, target_names=['Team2 Wins', 'Team1 Wins']))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    print("─────────────────────────────────────────────\n")

    return metrics
