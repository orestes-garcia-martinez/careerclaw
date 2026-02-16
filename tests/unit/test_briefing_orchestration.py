from pathlib import Path
from datetime import datetime, timezone

import careerclaw.briefing as briefing
from careerclaw.models import JobSource, NormalizedJob, UserProfile
from careerclaw.tracking import JsonTrackingRepository


def _fake_jobs() -> list[NormalizedJob]:
    t = datetime(2026, 2, 2, tzinfo=timezone.utc)
    return [
        NormalizedJob(
            source=JobSource.HN_WHO_IS_HIRING,
            title="Senior Frontend Engineer",
            company="A",
            description="React TypeScript Python AWS",
            location="Remote",
            posted_at=t,
            canonical_url="https://example.com/a",
        ),
        NormalizedJob(
            source=JobSource.REMOTEOK,
            title="Platform Engineer",
            company="B",
            description="Python AWS Observability",
            location="Remote",
            posted_at=t,
            canonical_url="https://example.com/b",
        ),
        NormalizedJob(
            source=JobSource.HN_WHO_IS_HIRING,
            title="Software Engineer",
            company="C",
            description="React TypeScript",
            location="Remote",
            posted_at=t,
            canonical_url="https://example.com/c",
        ),
    ]


def _profile() -> UserProfile:
    return UserProfile(
        skills=["react", "typescript", "python", "aws", "observability"],
        target_roles=["frontend engineer", "software engineer", "platform engineer"],
        experience_years=8,
        work_mode="remote",
        resume_summary="Systems-thinking engineer.",
        salary_min=140000,
        salary_max=190000,
    )


def test_briefing_dry_run_writes_nothing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(briefing, "fetch_all_jobs", lambda: _fake_jobs())

    repo = JsonTrackingRepository(tmp_path)

    result = briefing.run_daily_briefing(
        user_id="test-user",
        profile=_profile(),
        top_k=3,
        repo=repo,
        dry_run=True,
    )

    assert result.dry_run is True
    assert not (tmp_path / "tracking.json").exists()
    assert not (tmp_path / "runs.jsonl").exists()


def test_briefing_normal_run_writes_tracking_and_runlog(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(briefing, "fetch_all_jobs", lambda: _fake_jobs())

    repo = JsonTrackingRepository(tmp_path)

    result = briefing.run_daily_briefing(
        user_id="test-user",
        profile=_profile(),
        top_k=3,
        repo=repo,
        dry_run=False,
    )

    assert result.tracking_created == 3
    assert (tmp_path / "tracking.json").exists()
    assert (tmp_path / "runs.jsonl").exists()

    # re-run should dedupe saved jobs
    result2 = briefing.run_daily_briefing(
        user_id="test-user",
        profile=_profile(),
        top_k=3,
        repo=repo,
        dry_run=False,
    )
    assert result2.tracking_created == 0
    assert result2.tracking_already_present == 3
