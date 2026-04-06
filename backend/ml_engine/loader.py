"""Artifact loader/saver helpers for ML model versions."""
from __future__ import annotations

import json
import os
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BUNDLE_FILENAME = 'model_bundle.pkl'
METADATA_FILENAME = 'metadata.json'


def ensure_version_dir(model_path: str, version: str) -> Path:
	version_dir = Path(model_path) / version
	version_dir.mkdir(parents=True, exist_ok=True)
	return version_dir


def save_bundle(model_path: str, version: str, bundle: dict[str, Any], metadata: dict[str, Any]) -> dict[str, str]:
	version_dir = ensure_version_dir(model_path, version)
	bundle_path = version_dir / BUNDLE_FILENAME
	metadata_path = version_dir / METADATA_FILENAME

	with bundle_path.open('wb') as fp:
		pickle.dump(bundle, fp)

	metadata_payload = {
		**metadata,
		'version': version,
		'saved_at': datetime.now(timezone.utc).isoformat(),
		'bundle_file': BUNDLE_FILENAME,
	}
	with metadata_path.open('w', encoding='utf-8') as fp:
		json.dump(metadata_payload, fp, indent=2)

	return {'bundle': str(bundle_path), 'metadata': str(metadata_path)}


def load_bundle(model_path: str, version: str) -> dict[str, Any] | None:
	bundle_path = Path(model_path) / version / BUNDLE_FILENAME
	if not bundle_path.exists():
		return None
	with bundle_path.open('rb') as fp:
		return pickle.load(fp)


def load_metadata(model_path: str, version: str) -> dict[str, Any]:
	metadata_path = Path(model_path) / version / METADATA_FILENAME
	if not metadata_path.exists():
		return {}
	with metadata_path.open('r', encoding='utf-8') as fp:
		return json.load(fp)


def latest_version(model_path: str) -> str | None:
	base = Path(model_path)
	if not base.exists():
		return None
	candidates = [p.name for p in base.iterdir() if p.is_dir()]
	if not candidates:
		return None
	# Lexicographic works for v1.0, v1.1, v2.0 naming.
	return sorted(candidates)[-1]


def list_versions(model_path: str) -> list[str]:
	base = Path(model_path)
	if not base.exists():
		return []
	return sorted([p.name for p in base.iterdir() if p.is_dir()])


def _safe_float(value: Any, default: float) -> float:
	try:
		return float(value)
	except (TypeError, ValueError):
		return default


def _safe_int(value: Any, default: int) -> int:
	try:
		return int(value)
	except (TypeError, ValueError):
		return default


def compute_version_ranking(version: str, metadata: dict[str, Any]) -> dict[str, Any]:
	"""Compute a transparent score card for one model artifact version."""
	model_type = str(metadata.get('model_type') or '').strip().lower()
	accuracy = _safe_float(metadata.get('accuracy'), 0.0)
	auc_roc = _safe_float(metadata.get('auc_roc'), 0.0)
	brier = _safe_float(metadata.get('brier_score'), 1.0)
	sample_count = _safe_int(metadata.get('sample_count'), 0)

	quality_bonus = 0.1 if model_type == 'sklearn_ensemble' else 0.0
	size_bonus = min(sample_count / 50000.0, 0.1)
	brier_term = 1.0 - min(max(brier, 0.0), 1.0)

	score = (
		(0.45 * accuracy)
		+ (0.45 * auc_roc)
		+ (0.10 * brier_term)
		+ quality_bonus
		+ size_bonus
	)

	return {
		'version': version,
		'model_type': model_type or 'unknown',
		'accuracy': accuracy,
		'auc_roc': auc_roc,
		'brier_score': brier,
		'sample_count': sample_count,
		'score': round(score, 6),
		'components': {
			'accuracy_component': round(0.45 * accuracy, 6),
			'auc_component': round(0.45 * auc_roc, 6),
			'brier_component': round(0.10 * brier_term, 6),
			'quality_bonus': round(quality_bonus, 6),
			'size_bonus': round(size_bonus, 6),
		},
	}


def rank_versions(model_path: str) -> list[dict[str, Any]]:
	"""Rank versions by model score with explicit component breakdown."""
	ranked: list[dict[str, Any]] = []
	for version in list_versions(model_path):
		if not bundle_exists(model_path, version):
			continue
		meta = load_metadata(model_path, version)
		ranked.append(compute_version_ranking(version, meta))

	if not ranked:
		return []

	return sorted(ranked, key=lambda row: (row.get('score') or 0.0, row.get('version') or ''), reverse=True)


def select_best_version(model_path: str) -> str | None:
	"""Select the best model version from metadata metrics when available."""
	ranked = rank_versions(model_path)
	if ranked:
		return str(ranked[0].get('version') or '') or latest_version(model_path)
	return latest_version(model_path)


def bundle_exists(model_path: str, version: str) -> bool:
	return os.path.exists(Path(model_path) / version / BUNDLE_FILENAME)
