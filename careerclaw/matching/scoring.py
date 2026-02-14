from __future__ import annotations

from typing import Any, Dict, Optional, Set, Tuple

from .text import tokenize, tokens_from_list


def clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)


def experience_alignment_score(user_years: float, job_years: float) -> float:
    # Your clamped linear approach (deterministic + clean)
    if job_years is None or job_years <= 0:
        return 1.0
    if user_years is None:
        return 0.5  # neutral if user omitted experience
    return min(1.0, user_years / job_years)


def salary_alignment_score(
        user_min_annual_usd: Optional[float],
        job_min_annual_usd: Optional[float],
        job_max_annual_usd: Optional[float],
) -> float:
    """
    IMPORTANT CONTRACT: These inputs must be normalized to Annual USD by ingestion.
    If not available, pass None and we return neutral (0.5).
    """
    # Rule 0: If user doesn't specify a floor, treat salary as neutral.
    if not user_min_annual_usd or user_min_annual_usd <= 0:
        return 0.5

    # Rule 1: Missing Data
    if not job_min_annual_usd or not job_max_annual_usd:
        return 0.5

    # Guard: swapped ranges
    if job_max_annual_usd < job_min_annual_usd:
        job_min_annual_usd, job_max_annual_usd = job_max_annual_usd, job_min_annual_usd

    # Rule 2: Perfect Match (Job starts at or above user floor)
    if job_min_annual_usd >= user_min_annual_usd:
        return 1.0

    # Rule 3: Partial Match (User floor within range)
    if job_min_annual_usd < user_min_annual_usd <= job_max_annual_usd:
        # MVP: stable constant for "within range"
        return 0.8

    # Rule 4: Hard mismatch (Job max below user floor)
    # Score decays proportional to how far below; keep bounded and deterministic.
    return clamp01((job_max_annual_usd / user_min_annual_usd) * 0.5)


def keyword_overlap_score(
        user_keywords: Set[str],
        job_title: str,
        job_description: str,
        job_tags: Set[str],
) -> Tuple[float, Dict[str, Any]]:
    """
    Deterministic overlap:
    - Title overlap weighted heavier than body overlap
    - Tags add a small bump
    Returns score in [0,1] and a details dict for explanations.
    """
    if not user_keywords:
        return 0.0, {"reason": "no_user_keywords"}

    title_tokens = tokenize(job_title or "")
    body_tokens = tokenize(job_description or "")
    tags_tokens = set(t.lower() for t in (job_tags or set()))

    title_hits = user_keywords & title_tokens
    body_hits = user_keywords & body_tokens
    tag_hits = user_keywords & tags_tokens

    # Weighted hits: title counts double, tags small bump
    weighted_hit_count = (2 * len(title_hits)) + (1 * len(body_hits)) + (1 * len(tag_hits))
    # Normalize against a cap so long descriptions don't inflate unboundedly.
    # The denominator is a soft cap based on user keyword size.
    denom = max(8.0, min(20.0, float(len(user_keywords)) * 2.0))

    score = clamp01(weighted_hit_count / denom)

    details = {
        "title_hits": sorted(title_hits),
        "body_hits": sorted(body_hits),
        "tag_hits": sorted(tag_hits),
        "weighted_hit_count": weighted_hit_count,
        "denom": denom,
    }
    return score, details


def location_alignment_score(user_pref: Optional[str], job_location: Optional[str], job_tags: Set[str]) -> float:
    """
    MVP heuristic:
    - If user_pref is missing => neutral (0.5)
    - If user wants remote and job looks remote => 1.0 else 0.2
    - If user wants onsite and job says remote => 0.2 else 0.8 (not enough data)
    - Hybrid => 0.7 unless strong mismatch
    """
    if not user_pref:
        return 0.5

    pref = user_pref.strip().lower()
    loc = (job_location or "").lower()
    tags = set(t.lower() for t in (job_tags or set()))

    looks_remote = ("remote" in loc) or ("remote" in tags) or ("worldwide" in loc) or ("anywhere" in loc)

    if pref == "remote":
        return 1.0 if looks_remote else 0.2
    if pref == "onsite":
        return 0.2 if looks_remote else 0.8
    if pref == "hybrid":
        return 0.2 if looks_remote and "hybrid" not in loc else 0.7

    return 0.5  # unknown preference
