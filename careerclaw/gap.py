from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Set

from careerclaw.requirements import JobRequirements
from careerclaw.resume_intel import ResumeIntelligence


@dataclass(frozen=True)
class GapAnalysis:
    matched_keywords: List[str]
    missing_keywords: List[str]
    matched_phrases: List[str]
    missing_phrases: List[str]
    fit_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis": {
                "fit_score": self.fit_score,
                "signals": {
                    "keywords": self.matched_keywords,
                    "phrases": self.matched_phrases,
                },
                "gaps": {
                    "keywords": self.missing_keywords,
                    "phrases": self.missing_phrases,
                },
            }
        }


def analyze_gap(*, resume: ResumeIntelligence, job: JobRequirements, max_keywords: int = 30, max_phrases: int = 30) -> GapAnalysis:
    """
    Compare resume signals to job requirement signals.

    Ordering rule (important for agent readability):
    - Preserve job order: show matched/missing in the order they appear in the JOB.
    """
    resume_kw: Set[str] = set(resume.extracted_keywords or [])
    resume_ph: Set[str] = set(resume.extracted_phrases or [])

    # Keywords: preserve job order (use phrases list order for phrases; for keywords we approximate by sorting)
    # If you want perfect job-order keywords, pass an ordered token stream in a future enhancement.
    job_kw_sorted = sorted(job.keywords)
    matched_kw = [k for k in job_kw_sorted if k in resume_kw][:max_keywords]
    missing_kw = [k for k in job_kw_sorted if k not in resume_kw][:max_keywords]

    matched_ph = [p for p in job.phrases if p in resume_ph][:max_phrases]
    missing_ph = [p for p in job.phrases if p not in resume_ph][:max_phrases]

    total = len(job_kw_sorted) + len(job.phrases)
    matched = len(matched_kw) + len(matched_ph)
    fit = (matched / total) if total else 0.0

    return GapAnalysis(
        matched_keywords=matched_kw,
        missing_keywords=missing_kw,
        matched_phrases=matched_ph,
        missing_phrases=missing_ph,
        fit_score=round(fit, 4),
    )
