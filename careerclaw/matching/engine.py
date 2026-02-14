from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .scoring import (
    experience_alignment_score,
    keyword_overlap_score,
    location_alignment_score,
    salary_alignment_score,
    clamp01,
)
from .text import tokens_from_list
from .types import MatchBreakdown, ScoredJob


DEFAULT_WEIGHTS = {
    "keyword": 0.50,
    "experience": 0.20,
    "salary": 0.15,
    "location": 0.15,
}


def build_user_keywords(profile: Any) -> Set[str]:
    """
    Deterministic keyword bag:
    - skills
    - target roles
    - resume summary (optional)
    """
    skills = getattr(profile, "skills", []) or []
    target_roles = getattr(profile, "target_roles", []) or []
    summary = getattr(profile, "resume_summary", "") or ""

    kw = set()
    kw |= tokens_from_list(skills)
    kw |= tokens_from_list(target_roles)
    kw |= set(tokens_from_list([summary]))  # reuses tokenizer
    return kw


def score_job(profile: Any, job: Any, weights: Optional[Dict[str, float]] = None) -> ScoredJob:
    w = dict(DEFAULT_WEIGHTS)
    if weights:
        w.update(weights)

    user_keywords = build_user_keywords(profile)

    job_title = getattr(job, "title", "") or ""
    job_desc = getattr(job, "description", "") or ""
    job_loc = getattr(job, "location", None)
    job_tags = set(getattr(job, "tags", []) or [])

    # Experience inputs (job_years may not exist in MVP sources; treat missing as neutral via scoring func)
    user_years = (
        getattr(profile, "experience_years", None)   # <-- models.py contract
        or getattr(profile, "years_experience", None)
        or getattr(profile, "years_experience", None)  # (optional legacy alias, harmless)
    )
    job_years = getattr(job, "min_years_experience", None)

    # Add casting HERE
    user_years = float(user_years) if user_years is not None else None
    job_years = float(job_years) if job_years is not None else None

    # Salary inputs
    # Note: In MVP, many jobs won't have salary; scoring returns neutral (0.5) when missing.
    # If/when ingestion normalizes salary, prefer *_annual_usd fields automatically.
    user_min = (
        getattr(profile, "salary_min_annual_usd", None)
        or getattr(profile, "salary_min", None)  # <-- models.py contract
    )

    job_min = (
        getattr(job, "salary_min_annual_usd", None)
        or getattr(job, "salary_min", None)
    )
    job_max = (
        getattr(job, "salary_max_annual_usd", None)
        or getattr(job, "salary_max", None)
    )

    # User location pref
    user_loc_pref = (
        getattr(profile, "work_mode", None)            # <-- models.py contract
        or getattr(profile, "preferred_location", None)
        or getattr(profile, "location_preference", None)
        or getattr(profile, "location", None)          # <-- models.py optional
    )

    k_score, k_details = keyword_overlap_score(user_keywords, job_title, job_desc, job_tags)
    e_score = experience_alignment_score(user_years, job_years)
    s_score = salary_alignment_score(user_min, job_min, job_max)
    l_score = location_alignment_score(user_loc_pref, job_loc, job_tags)

    total = (
            (k_score * w["keyword"])
            + (e_score * w["experience"])
            + (s_score * w["salary"])
            + (l_score * w["location"])
    )
    total = clamp01(total)

    breakdown = MatchBreakdown(
        total_score=total,
        keyword_score=k_score,
        experience_score=e_score,
        salary_score=s_score,
        location_score=l_score,
        details={
            "weights": w,
            "keyword_details": k_details,
            "experience": {"user_years": user_years, "job_years": job_years},
            "salary": {
                "user_min_annual_usd": user_min,
                "job_min_annual_usd": job_min,
                "job_max_annual_usd": job_max,
                "note": "salary inputs expected normalized to Annual USD during ingestion",
            },
            "location": {
                "user_pref": user_loc_pref,
                "job_location": job_loc,
                "job_tags": sorted(job_tags),
            },
        },
    )

    return ScoredJob(job=job, score=total, breakdown=breakdown)


def rank_jobs(profile: Any, jobs: Sequence[Any], top_n: int = 3) -> List[ScoredJob]:
    scored = [score_job(profile, j) for j in jobs]
    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_n]
