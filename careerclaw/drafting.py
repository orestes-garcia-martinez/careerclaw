from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

from careerclaw.models import NormalizedJob, UserProfile
from careerclaw.matching.text import tokenize


class DraftEnhancer(Protocol):
    def enhance(self, *, base_draft: str, profile: UserProfile, job: NormalizedJob) -> str:
        ...


@dataclass(frozen=True)
class DraftResult:
    job_id: str
    draft: str
    channel: str = "email"   # MVP default
    enhanced: bool = False   # True when produced by LLMDraftEnhancer


def _pick_relevant_skills(profile: UserProfile, job: NormalizedJob, max_skills: int = 4) -> list[str]:
    hay = f"{job.title} {job.description} {' '.join(job.tags or [])}"
    tokens = tokenize(hay)

    hits: list[str] = []
    for s in profile.skills:
        ss = (s or "").strip()
        if not ss:
            continue

        low = ss.lower()

        # If skill is very short, skip matching (avoid go->good)
        if len(low) < 3:
            continue

        if " " in low:
            # Multi-word: substring match is acceptable for MVP
            if low in hay.lower():
                hits.append(ss)
        else:
            # Single-word: match whole tokens
            if low in tokens:
                hits.append(ss)

        if len(hits) >= max_skills:
            break

    return hits or profile.skills[: min(max_skills, len(profile.skills))]


def draft_outreach(
        *,
        profile: UserProfile,
        job: NormalizedJob,
        enhancer: Optional[DraftEnhancer] = None,
) -> DraftResult:
    """
    MVP: deterministic 150–250 word outreach.
    Optional enhancer hook can be added later (Pro gate).
    """
    skills = _pick_relevant_skills(profile, job)
    skills_line = ", ".join(skills)

    company = job.company or "your team"
    title = job.title or "this role"

    base = f"""Subject: Interest in {title} at {company}

Hi {company} team,

I'm reaching out to express interest in the {title} role. I have {profile.experience_years}+ years of experience and a strong track record of delivering results in my field.

From the posting, it looks like you’re looking for someone with experience in {skills_line}. That aligns well with my background, including:
- Delivering high-quality work with strong ownership and attention to outcomes
- Communicating clearly and collaborating effectively with colleagues and stakeholders
- Identifying problems quickly and following through with practical, lasting solutions

If helpful, I can share a brief summary of relevant work and walk through how I'd approach the first 30 days in this role. Thanks for your time — I'd welcome the chance to connect.

Best regards,
[Your Name]
"""

    draft = base.strip()

    if enhancer is not None:
        draft = enhancer.enhance(base_draft=draft, profile=profile, job=job).strip()

    return DraftResult(job_id=job.job_id, draft=draft)
