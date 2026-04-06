"""Helpers for lightweight men/women cricket segmentation."""

from __future__ import annotations

import re


_WOMEN_PATTERNS = (
    re.compile(r"\bwomen\b", re.IGNORECASE),
    re.compile(r"\bwomen's\b", re.IGNORECASE),
    re.compile(r"\bladies\b", re.IGNORECASE),
    re.compile(r"\bgirls\b", re.IGNORECASE),
    re.compile(r"\b[A-Z]{2,4}-W\b", re.IGNORECASE),
    re.compile(r"\b[A-Z]{2,6}W\b", re.IGNORECASE),
    re.compile(r"\([Ww]\)"),
)


def is_womens_cricket_text(*parts: object) -> bool:
    text = " ".join(str(part or "") for part in parts)
    if not text.strip():
        return False
    return any(pattern.search(text) for pattern in _WOMEN_PATTERNS)


def infer_match_gender_bucket(match) -> str:
    """Return "women" for women's cricket, otherwise default to "men"."""
    team1_name = getattr(getattr(match, "team1", None), "name", "")
    team2_name = getattr(getattr(match, "team2", None), "name", "")
    if is_womens_cricket_text(
        getattr(match, "name", ""),
        getattr(match, "series_name", ""),
        team1_name,
        team2_name,
    ):
        return "women"
    return "men"
