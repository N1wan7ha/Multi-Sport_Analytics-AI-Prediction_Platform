"""Smoke-test model artifacts by running synthetic prediction tasks.

Usage examples:
  python backend/ml_engine/model_task_smoke_test.py
  python backend/ml_engine/model_task_smoke_test.py --artifact-dir artifacts/v2.3-dataset4_20260326_115942
  python backend/ml_engine/model_task_smoke_test.py --num-tasks 200
"""
from __future__ import annotations

import argparse
import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class ArtifactBundle:
    artifact_dir: Path
    metadata: dict[str, Any]
    model: Any
    scaler: Any


def _workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _artifacts_root() -> Path:
    return _workspace_root() / "artifacts"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_pickle(path: Path) -> Any:
    with path.open("rb") as f:
        return pickle.load(f)


def _is_valid_artifact_dir(path: Path) -> bool:
    required = ["metadata.json", "model_bundle.pkl", "scaler.pkl"]
    return path.is_dir() and all((path / name).exists() for name in required)


def _discover_latest_artifact(artifacts_dir: Path) -> Path:
    candidates = [p for p in artifacts_dir.iterdir() if _is_valid_artifact_dir(p)]
    if not candidates:
        raise FileNotFoundError(
            f"No valid artifact directory found under: {artifacts_dir}. "
            "Expected directories containing metadata.json, model_bundle.pkl, scaler.pkl"
        )

    # Prefer dataset4/base json style versions, then fallback to newest mtime.
    preferred = [p for p in candidates if p.name.startswith("v2.")]
    ranked = preferred if preferred else candidates
    ranked = sorted(ranked, key=lambda p: p.stat().st_mtime, reverse=True)
    return ranked[0]


def _load_bundle(artifact_dir: Path) -> ArtifactBundle:
    metadata = _load_json(artifact_dir / "metadata.json")
    model = _load_pickle(artifact_dir / "model_bundle.pkl")
    scaler = _load_pickle(artifact_dir / "scaler.pkl")
    return ArtifactBundle(artifact_dir=artifact_dir, metadata=metadata, model=model, scaler=scaler)


def _feature_names_from_metadata(metadata: dict[str, Any]) -> list[str]:
    names = metadata.get("feature_names")
    if isinstance(names, list) and names:
        return [str(v) for v in names]

    count = metadata.get("feature_count")
    if isinstance(count, int) and count > 0:
        return [f"feature_{i}" for i in range(count)]

    raise ValueError("Could not infer features from metadata (missing feature_names and feature_count).")


def _task_vector(feature_names: list[str]) -> pd.DataFrame:
    vals: list[float] = []
    for idx, name in enumerate(feature_names):
        lname = name.lower()
        if "year" in lname:
            vals.append(2024.0)
        elif "month" in lname:
            vals.append(6.0)
        elif "dayofweek" in lname:
            vals.append(2.0)
        elif "day" in lname:
            vals.append(15.0)
        elif "team_1" in lname:
            vals.append(1.0)
        elif "team_2" in lname:
            vals.append(2.0)
        elif "match_number" in lname:
            vals.append(25.0)
        else:
            vals.append(float((idx % 7) + 1))

    return pd.DataFrame([vals], columns=feature_names, dtype=float)


def _batch_vectors(num_tasks: int, feature_names: list[str], seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    arr = rng.normal(loc=0.0, scale=1.0, size=(num_tasks, len(feature_names))).astype(float)
    return pd.DataFrame(arr, columns=feature_names)


def run_task_test(bundle: ArtifactBundle, num_tasks: int) -> dict[str, Any]:
    feature_names = _feature_names_from_metadata(bundle.metadata)
    n_features = len(feature_names)

    # Single synthetic task.
    x_task = _task_vector(feature_names)
    x_task_scaled = bundle.scaler.transform(x_task)
    pred = bundle.model.predict(x_task_scaled)

    if hasattr(bundle.model, "predict_proba"):
        proba = bundle.model.predict_proba(x_task_scaled)
        top_class = int(np.argmax(proba[0]))
        top_prob = float(np.max(proba[0]))
        proba_sum = float(np.sum(proba[0]))
    else:
        top_class = int(pred[0])
        top_prob = float("nan")
        proba_sum = float("nan")

    # Batch consistency task.
    x_batch = _batch_vectors(num_tasks=num_tasks, feature_names=feature_names)
    x_batch_scaled = bundle.scaler.transform(x_batch)
    batch_pred = bundle.model.predict(x_batch_scaled)

    batch_unique = int(np.unique(batch_pred).size)
    batch_ok = bool(np.isfinite(x_batch_scaled).all())

    if hasattr(bundle.model, "predict_proba"):
        batch_proba = bundle.model.predict_proba(x_batch_scaled)
        batch_prob_sums = batch_proba.sum(axis=1)
        probs_close = bool(np.allclose(batch_prob_sums, 1.0, atol=1e-6))
    else:
        probs_close = True

    return {
        "artifact_dir": str(bundle.artifact_dir),
        "version": str(bundle.metadata.get("version", bundle.artifact_dir.name)),
        "feature_count": n_features,
        "single_task": {
            "predicted_class": int(pred[0]),
            "top_class": top_class,
            "top_probability": top_prob,
            "probability_sum": proba_sum,
        },
        "batch_task": {
            "num_tasks": int(num_tasks),
            "unique_predicted_classes": batch_unique,
            "scaled_values_finite": batch_ok,
            "probabilities_sum_to_one": probs_close,
        },
        "status": "pass" if batch_ok and probs_close else "warn",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run model artifact task smoke tests.")
    parser.add_argument(
        "--artifact-dir",
        type=str,
        default="",
        help="Optional artifact directory. If omitted, latest valid artifact in artifacts/ is used.",
    )
    parser.add_argument("--num-tasks", type=int, default=100, help="Batch task size for consistency testing.")
    parser.add_argument(
        "--save-json",
        type=str,
        default="",
        help="Optional path to save test result JSON.",
    )
    args = parser.parse_args()

    artifacts_dir = _artifacts_root()
    if args.artifact_dir:
        artifact_dir = (_workspace_root() / args.artifact_dir).resolve()
    else:
        artifact_dir = _discover_latest_artifact(artifacts_dir)

    if not _is_valid_artifact_dir(artifact_dir):
        raise FileNotFoundError(
            f"Invalid artifact directory: {artifact_dir}. "
            "Required: metadata.json, model_bundle.pkl, scaler.pkl"
        )

    bundle = _load_bundle(artifact_dir)
    result = run_task_test(bundle, num_tasks=max(10, int(args.num_tasks)))

    print("=== Model Task Smoke Test ===")
    print(json.dumps(result, indent=2))

    if args.save_json:
        out_path = (_workspace_root() / args.save_json).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Saved result JSON: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
