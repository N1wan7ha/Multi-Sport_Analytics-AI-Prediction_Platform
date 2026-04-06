"""Weaviate vector-context integration for prediction enhancement.

This module is intentionally optional and fail-safe:
- If Weaviate is unavailable, prediction flow continues unchanged.
- Enable behavior via ML_VECTOR_CONTEXT_ENABLED in settings/.env.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

import httpx
from django.conf import settings

from apps.matches.models import Match

logger = logging.getLogger(__name__)


@dataclass
class VectorAdjustment:
    enabled: bool
    available: bool
    applied: bool
    context_count: int
    team1_bias: float
    probability_shift: float
    query: str
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["team1_bias"] = round(float(payload.get("team1_bias", 0.0)), 6)
        payload["probability_shift"] = round(float(payload.get("probability_shift", 0.0)), 6)
        return payload


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _escape_graphql(value: str) -> str:
    return (value or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").strip()


def _stable_object_id(match_id: int) -> str:
    digest = hashlib.sha1(f"match-context-{match_id}".encode("utf-8")).hexdigest()[:32]
    return f"{digest[0:8]}-{digest[8:12]}-{digest[12:16]}-{digest[16:20]}-{digest[20:32]}"


def _to_rfc3339_date(value: date | None) -> str | None:
    if not value:
        return None
    return f"{value.isoformat()}T00:00:00Z"


class WeaviateContextClient:
    """Small HTTP client wrapper around Weaviate REST/GraphQL endpoints."""

    def __init__(self):
        self.base_url = str(getattr(settings, "WEAVIATE_URL", "http://localhost:8080")).rstrip("/")
        self.class_name = str(getattr(settings, "WEAVIATE_CLASS_NAME", "MatchContext")).strip() or "MatchContext"
        self.timeout = float(getattr(settings, "WEAVIATE_TIMEOUT_SECONDS", 3.0) or 3.0)
        self.api_key = str(getattr(settings, "WEAVIATE_API_KEY", "") or "").strip()

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.request(method, url, headers=self._headers(), json=payload)
            if response.status_code >= 400:
                logger.debug("Weaviate request failed [%s] %s: %s", response.status_code, path, response.text)
                return None
            if not response.text.strip():
                return {}
            return response.json()
        except Exception as exc:
            logger.debug("Weaviate connection error on %s %s: %s", method, path, exc)
            return None

    def is_ready(self) -> bool:
        payload = self._request("GET", "/v1/.well-known/ready")
        return payload is not None

    def ensure_schema(self) -> bool:
        schema = self._request("GET", "/v1/schema")
        if schema is None:
            return False

        classes = schema.get("classes", []) if isinstance(schema, dict) else []
        if any(str(item.get("class", "")).strip() == self.class_name for item in classes if isinstance(item, dict)):
            return True

        create_payload = {
            "class": self.class_name,
            "description": "Cricket match context for semantic retrieval",
            "vectorizer": "none",
            "properties": [
                {"name": "match_id", "dataType": ["int"]},
                {"name": "team1", "dataType": ["text"]},
                {"name": "team2", "dataType": ["text"]},
                {"name": "winner_team", "dataType": ["text"]},
                {"name": "format", "dataType": ["text"]},
                {"name": "venue", "dataType": ["text"]},
                {"name": "played_on", "dataType": ["date"]},
                {"name": "source", "dataType": ["text"]},
                {"name": "summary", "dataType": ["text"]},
            ],
        }
        created = self._request("POST", "/v1/schema", create_payload)
        return created is not None

    def upsert_context(self, match_id: int, properties: dict[str, Any]) -> bool:
        object_id = _stable_object_id(match_id)
        create_payload = {
            "id": object_id,
            "class": self.class_name,
            "properties": properties,
        }
        # First try create. If the object already exists, PATCH updates in-place.
        out = self._request("POST", "/v1/objects", create_payload)
        if out is not None:
            return True

        update_payload = {
            "class": self.class_name,
            "properties": properties,
        }
        out = self._request("PATCH", f"/v1/objects/{object_id}", update_payload)
        return out is not None

    def _query_graphql(self, query: str) -> list[dict[str, Any]]:
        payload = self._request("POST", "/v1/graphql", {"query": query})
        if payload is None:
            return []

        errors = payload.get("errors") if isinstance(payload, dict) else None
        if errors:
            return []

        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        get_data = data.get("Get", {}) if isinstance(data, dict) else {}
        rows = get_data.get(self.class_name, []) if isinstance(get_data, dict) else []
        return rows if isinstance(rows, list) else []

    def search_contexts(self, query_text: str, top_k: int = 6, exclude_match_id: int | None = None) -> list[dict[str, Any]]:
        q = _escape_graphql(query_text)
        # Try semantic-like hybrid first (works when vector modules exist), then BM25 fallback.
        gql_hybrid = f'''{{
  Get {{
    {self.class_name}(
      hybrid: {{query: "{q}", alpha: 0.75}}
      limit: {max(1, int(top_k))}
    ) {{
      match_id
      team1
      team2
      winner_team
      source
      summary
      _additional {{ score certainty distance id }}
    }}
  }}
}}'''
        rows = self._query_graphql(gql_hybrid)

        if not rows:
            gql_bm25 = f'''{{
  Get {{
    {self.class_name}(
      bm25: {{query: "{q}"}}
      limit: {max(1, int(top_k))}
    ) {{
      match_id
      team1
      team2
      winner_team
      source
      summary
      _additional {{ score certainty distance id }}
    }}
  }}
}}'''
            rows = self._query_graphql(gql_bm25)

        if exclude_match_id is None:
            return rows

        filtered: list[dict[str, Any]] = []
        for row in rows:
            row_match_id = int(_safe_float(row.get("match_id"), default=-1))
            if row_match_id == int(exclude_match_id):
                continue
            filtered.append(row)
        return filtered


def _match_summary_text(match: Match) -> str:
    team1 = (match.team1.name if match.team1 else "Unknown")
    team2 = (match.team2.name if match.team2 else "Unknown")
    winner = (match.winner.name if match.winner else "Unknown")
    venue = (match.venue.name if match.venue else "Unknown venue")
    date_text = str(match.match_date) if match.match_date else "unknown-date"
    result_text = str(match.result_text or "").strip()
    toss_text = ""
    if match.toss_winner:
        toss_text = f" Toss won by {match.toss_winner.name} ({match.toss_decision or 'unknown'})."

    return (
        f"{team1} vs {team2}. Format: {match.format}. Venue: {venue}. "
        f"Date: {date_text}. Winner: {winner}. {result_text}{toss_text}"
    ).strip()


def build_prediction_query_text(match: Match) -> str:
    team1 = match.team1.name if match.team1 else "Unknown"
    team2 = match.team2.name if match.team2 else "Unknown"
    venue = match.venue.name if match.venue else "Unknown venue"
    return f"{team1} vs {team2} {match.format} at {venue}"


def _context_weight(row: dict[str, Any]) -> float:
    extra_raw = row.get("_additional")
    extra = extra_raw if isinstance(extra_raw, dict) else {}
    certainty = _safe_float(extra.get("certainty"), default=-1.0)
    if 0.0 <= certainty <= 1.0:
        return certainty

    score = _safe_float(extra.get("score"), default=0.0)
    if score > 0:
        return min(score, 1.0)

    distance = _safe_float(extra.get("distance"), default=-1.0)
    if distance >= 0:
        return _clamp(1.0 - distance, 0.0, 1.0)

    return 0.5


def compute_team1_bias_from_contexts(
    contexts: list[dict[str, Any]],
    team1_name: str,
    team2_name: str,
) -> tuple[float, int]:
    if not contexts:
        return 0.0, 0

    t1 = (team1_name or "").strip().lower()
    t2 = (team2_name or "").strip().lower()
    if not t1 or not t2:
        return 0.0, len(contexts)

    weighted_sum = 0.0
    weight_total = 0.0
    for row in contexts:
        winner = str(row.get("winner_team") or "").strip().lower()
        if not winner:
            continue

        sign = 0.0
        if winner == t1:
            sign = 1.0
        elif winner == t2:
            sign = -1.0
        else:
            continue

        w = _context_weight(row)
        weighted_sum += sign * w
        weight_total += w

    if weight_total <= 0:
        return 0.0, len(contexts)

    bias = weighted_sum / weight_total
    return _clamp(float(bias), -1.0, 1.0), len(contexts)


def index_completed_matches_to_weaviate(limit: int = 0, since_date: date | None = None) -> dict[str, Any]:
    """Index completed matches into Weaviate for context retrieval."""
    enabled = bool(getattr(settings, "ML_VECTOR_CONTEXT_ENABLED", False))
    if not enabled:
        return {
            "status": "skipped",
            "reason": "ML_VECTOR_CONTEXT_ENABLED is false",
            "indexed": 0,
            "failed": 0,
        }

    client = WeaviateContextClient()
    if not client.is_ready():
        return {
            "status": "unavailable",
            "reason": "Weaviate is not reachable",
            "indexed": 0,
            "failed": 0,
        }

    if not client.ensure_schema():
        return {
            "status": "schema_error",
            "reason": "Could not ensure Weaviate schema",
            "indexed": 0,
            "failed": 0,
        }

    qs = Match.objects.select_related("team1", "team2", "winner", "venue").filter(
        status="complete",
        team1__isnull=False,
        team2__isnull=False,
    ).order_by("-match_date", "-id")

    if since_date is not None:
        qs = qs.filter(match_date__gte=since_date)

    if int(limit or 0) > 0:
        qs = qs[: int(limit)]

    indexed = 0
    failed = 0

    for match in qs:
        match_pk = int(getattr(match, 'pk', 0) or 0)
        properties = {
            "match_id": match_pk,
            "team1": match.team1.name if match.team1 else "",
            "team2": match.team2.name if match.team2 else "",
            "winner_team": match.winner.name if match.winner else "",
            "format": str(match.format or ""),
            "venue": match.venue.name if match.venue else "",
            "source": "historical_match",
            "summary": _match_summary_text(match),
        }
        played_on = _to_rfc3339_date(match.match_date)
        if played_on:
            properties["played_on"] = played_on
        ok = client.upsert_context(match_pk, properties)
        if ok:
            indexed += 1
        else:
            failed += 1

    return {
        "status": "ok",
        "indexed": indexed,
        "failed": failed,
        "total": indexed + failed,
    }


def apply_weaviate_context_to_probability(
    match: Match,
    team1_probability: float,
    top_k: int = 6,
) -> tuple[float, dict[str, Any], dict[str, Any] | None]:
    """Return (adjusted_probability, metadata, optional_key_factor)."""
    enabled = bool(getattr(settings, "ML_VECTOR_CONTEXT_ENABLED", False))
    if not enabled:
        info = VectorAdjustment(
            enabled=False,
            available=False,
            applied=False,
            context_count=0,
            team1_bias=0.0,
            probability_shift=0.0,
            query="",
            reason="disabled",
        )
        return team1_probability, info.as_dict(), None

    client = WeaviateContextClient()
    if not client.is_ready():
        info = VectorAdjustment(
            enabled=True,
            available=False,
            applied=False,
            context_count=0,
            team1_bias=0.0,
            probability_shift=0.0,
            query="",
            reason="weaviate_unavailable",
        )
        return team1_probability, info.as_dict(), None

    query = build_prediction_query_text(match)
    match_pk = int(getattr(match, 'pk', 0) or 0)
    contexts = client.search_contexts(query_text=query, top_k=max(1, int(top_k)), exclude_match_id=match_pk)

    team1_name = match.team1.name if match.team1 else ""
    team2_name = match.team2.name if match.team2 else ""
    team1_bias, context_count = compute_team1_bias_from_contexts(contexts, team1_name, team2_name)

    max_shift = float(getattr(settings, "ML_VECTOR_MAX_PROB_SHIFT", 0.06) or 0.06)
    shift = _clamp(team1_bias, -1.0, 1.0) * max(0.0, max_shift)
    adjusted_probability = _clamp(float(team1_probability) + shift, 0.05, 0.95)
    applied = bool(context_count > 0 and abs(shift) >= 0.005)

    info = VectorAdjustment(
        enabled=True,
        available=bool(context_count > 0),
        applied=applied,
        context_count=context_count,
        team1_bias=team1_bias,
        probability_shift=(adjusted_probability - float(team1_probability)),
        query=query,
    )

    key_factor = None
    if context_count > 0:
        key_factor = {
            "factor": "vector_context_bias",
            "impact": round(abs(info.probability_shift), 4),
            "direction": "team1" if info.probability_shift > 0 else "team2",
            "contexts": context_count,
        }

    return adjusted_probability, info.as_dict(), key_factor
