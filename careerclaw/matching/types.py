from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class MatchBreakdown:
    total_score: float
    keyword_score: float
    experience_score: float
    salary_score: float
    location_score: float
    # Human-friendly explanation payload (stable, deterministic)
    details: Dict[str, Any]


@dataclass(frozen=True)
class ScoredJob:
    job: Any  # NormalizedJob in your codebase
    score: float
    breakdown: MatchBreakdown
