from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from careerclaw.requirements import JobRequirements
from careerclaw.resume_intel import ResumeIntelligence


def _take_top(*, phrases: List[str], keywords: List[str], max_phrases: int = 5, max_keywords: int = 5) -> Dict[str, List[str]]:
    return {
        "phrases": phrases[:max_phrases],
        "keywords": keywords[:max_keywords],
    }


@dataclass(frozen=True)
class GapAnalysis:
    matched_keywords: List[str]
    missing_keywords: List[str]
    matched_phrases: List[str]
    missing_phrases: List[str]
    fit_score: float
    fit_score_unweighted: float

    def to_dict(self) -> Dict[str, Any]:
        summary = {
            "top_signals": _take_top(phrases=self.matched_phrases, keywords=self.matched_keywords),
            "top_gaps": _take_top(phrases=self.missing_phrases, keywords=self.missing_keywords),
        }
        return {
            "analysis": {
                "fit_score": self.fit_score,
                "fit_score_unweighted": self.fit_score_unweighted,
                "signals": {
                    "keywords": self.matched_keywords,
                    "phrases": self.matched_phrases,
                },
                "gaps": {
                    "keywords": self.missing_keywords,
                    "phrases": self.missing_phrases,
                },
                "summary": summary,
            }
        }


def analyze_gap(
        *,
        resume: ResumeIntelligence,
        job: JobRequirements,
        max_keywords: int = 30,
        max_phrases: int = 30,
        phrase_weight: float = 2.0,
        keyword_weight: float = 1.0,
        default_resume_weight: float = 0.6,
) -> GapAnalysis:
    """
    Compare resume signals to job requirement signals.

    Key design points (Phase-5D):
    - Preserve JOB order using job.keyword_stream and job.phrases.
    - Keep JSON machine-friendly by separating keywords vs phrases.
    - Compute a weighted fit_score:
        - phrases count more than keywords (phrase_weight > keyword_weight)
        - resume section weighting boosts confidence (skills/summary/experience)
    - Also compute fit_score_unweighted for interpretability/regression checking.
    """
    resume_kw_set = set(resume.extracted_keywords or [])
    resume_ph_set = set(resume.extracted_phrases or [])

    # Ordered lists based on JOB emphasis
    job_kw_stream = job.keyword_stream or []
    job_phrases = job.phrases or []

    matched_kw_all = [k for k in job_kw_stream if k in resume_kw_set]
    missing_kw_all = [k for k in job_kw_stream if k not in resume_kw_set]

    matched_ph_all = [p for p in job_phrases if p in resume_ph_set]
    missing_ph_all = [p for p in job_phrases if p not in resume_ph_set]

    # Visible (bounded) lists for readability
    matched_kw = matched_kw_all[:max_keywords]
    missing_kw = missing_kw_all[:max_keywords]
    matched_ph = matched_ph_all[:max_phrases]
    missing_ph = missing_ph_all[:max_phrases]

    # --- fit_score_unweighted (simple overlap / total) ---
    total_unweighted = len(job_kw_stream) + len(job_phrases)
    matched_unweighted = len(matched_kw_all) + len(matched_ph_all)
    fit_unweighted = (matched_unweighted / total_unweighted) if total_unweighted else 0.0

    # --- weighted fit_score ---
    # Weight per signal: base * resume_section_weight(signal)
    kw_weights = resume.keyword_weights or {}
    ph_weights = resume.phrase_weights or {}

    denom = 0.0
    numer = 0.0

    for k in job_kw_stream:
        denom += keyword_weight
        if k in resume_kw_set:
            rw = kw_weights.get(k, default_resume_weight)
            numer += keyword_weight * rw

    for p in job_phrases:
        denom += phrase_weight
        if p in resume_ph_set:
            rw = ph_weights.get(p, default_resume_weight)
            numer += phrase_weight * rw

    fit_weighted = (numer / denom) if denom else 0.0

    return GapAnalysis(
        matched_keywords=matched_kw,
        missing_keywords=missing_kw,
        matched_phrases=matched_ph,
        missing_phrases=missing_ph,
        fit_score=round(fit_weighted, 4),
        fit_score_unweighted=round(fit_unweighted, 4),
    )
