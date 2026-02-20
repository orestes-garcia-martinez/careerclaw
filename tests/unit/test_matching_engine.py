from dataclasses import dataclass
from careerclaw.models import UserProfile, NormalizedJob, JobSource
from careerclaw.matching.engine import rank_jobs

@dataclass
class Profile:
    skills: list
    target_roles: list
    resume_summary: str
    years_experience: float
    preferred_location: str
    salary_min_annual_usd: float

@dataclass
class Job:
    title: str
    description: str
    location: str
    tags: list
    salary_min_annual_usd: float | None = None
    salary_max_annual_usd: float | None = None
    min_years_experience: float | None = None

def test_rank_jobs_returns_top3_sorted():
    profile = Profile(
        skills=["React", "TypeScript", "AWS"],
        target_roles=["Frontend Engineer"],
        resume_summary="Built large-scale UI platforms and design systems.",
        years_experience=6,
        preferred_location="remote",
        salary_min_annual_usd=120000,
    )

    jobs = [
        Job(
            title="Senior Frontend Engineer (React)",
            description="React TypeScript design system",
            location="Remote",
            tags=["react", "typescript"],
            salary_min_annual_usd=140000,
            salary_max_annual_usd=180000,
            min_years_experience=5,
        ),
        Job(
            title="Backend Engineer",
            description="Python data pipelines",
            location="Remote",
            tags=["python"],
            salary_min_annual_usd=130000,
            salary_max_annual_usd=150000,
            min_years_experience=3,
        ),
        Job(
            title="Junior Web Developer",
            description="HTML CSS",
            location="Onsite",
            tags=["html", "css"],
            salary_min_annual_usd=50000,
            salary_max_annual_usd=70000,
            min_years_experience=1,
        ),
        Job(
            title="Frontend Engineer",
            description="React and AWS preferred",
            location="Remote - US",
            tags=["react", "aws"],
            salary_min_annual_usd=115000,
            salary_max_annual_usd=135000,
            min_years_experience=4,
        ),
    ]

    top = rank_jobs(profile, jobs, top_n=3)
    assert len(top) == 3
    assert top[0].score >= top[1].score >= top[2].score
    # The React senior role should win
    assert "frontend" in top[0].job.title.lower()

def test_engine_uses_models_userprofile_fields():
    profile = UserProfile(
        skills=["React", "TypeScript"],
        target_roles=["Frontend Engineer"],
        experience_years=6,
        work_mode="remote",
        resume_summary="Senior FE building platforms",
        salary_min=120000,
    )

    jobs = [
        NormalizedJob(
            source=JobSource.REMOTEOK,
            title="Senior Frontend Engineer (React)",
            company="Acme",
            description="React TypeScript",
            location="Remote",
            tags=["react", "typescript"],
            canonical_url="https://example.com/1",
            posted_at=None,
        ),
        NormalizedJob(
            source=JobSource.REMOTEOK,
            title="Onsite Junior Developer",
            company="Beta",
            description="HTML CSS",
            location="Onsite",
            tags=["html", "css"],
            canonical_url="https://example.com/2",
            posted_at=None,
        ),
    ]

    top = rank_jobs(profile, jobs, top_n=1)
    assert len(top) == 1
    assert "frontend" in top[0].job.title.lower()
    # ensure location preference is applied (remote should be favored)
    assert top[0].breakdown.location_score > 0.5