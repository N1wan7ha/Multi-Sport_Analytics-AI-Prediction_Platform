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


def bundle_exists(model_path: str, version: str) -> bool:
	return os.path.exists(Path(model_path) / version / BUNDLE_FILENAME)
