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


# ------------------------------------------------------------------
# PR-6: LLM enhancement integration tests
# ------------------------------------------------------------------

from unittest.mock import MagicMock, patch
from careerclaw.resume_intel import build_resume_intelligence
from careerclaw.llm.enhancer import DraftEnhancerError


def _resume_intel():
    return build_resume_intelligence(
        resume_summary="Senior engineer focused on systems thinking.",
        resume_text=None,
        skills=["react", "typescript", "python", "aws"],
        target_roles=["software engineer"],
    )


def _valid_enhanced_body():
    return (
        "Hi team, I noticed your posting and wanted to reach out directly. "
        "My background includes five years of production Python and React work, "
        "shipping features end to end from API design through frontend delivery. "
        "Most recently I led a platform migration that reduced p99 latency by 35 percent "
        "while improving observability across the stack. "
        "I have worked in fully remote distributed teams and thrive in high-ownership "
        "environments. I would be glad to share specifics about relevant projects "
        "if that would be helpful. Please feel free to reach out at your convenience."
    )


def test_briefing_json_output_has_enhanced_false_when_no_llm_key(tmp_path, monkeypatch):
    """Without CAREERCLAW_LLM_KEY, all drafts must have enhanced=False."""
    monkeypatch.delenv("CAREERCLAW_LLM_KEY", raising=False)
    monkeypatch.setattr(briefing, "fetch_all_jobs", lambda: _fake_jobs())

    import careerclaw.config as cfg
    import importlib
    importlib.reload(cfg)
    monkeypatch.setattr(briefing, "config", cfg)

    result = briefing.run_daily_briefing(
        user_id="test-user",
        profile=_profile(),
        top_k=3,
        dry_run=True,
        resume_intel=_resume_intel(),
    )

    d = result.to_dict()
    for draft in d["drafts"]:
        assert draft["enhanced"] is False, f"Expected enhanced=False but got: {draft}"


class BoomFailoverEnhancer:
    def __init__(self, *args, **kwargs):
        pass

    def enhance(self, *args, **kwargs):
        raise Exception("boom")  # could also raise DraftEnhancerError


def test_briefing_falls_back_to_deterministic_when_enhancer_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(briefing, "fetch_all_jobs", lambda: _fake_jobs())

    # Open LLM gate: must be Pro + llm_configured + resume_intel present
    monkeypatch.setattr(briefing.config, "pro_licensed", lambda: True)

    # Ensure CAREERCLAW_LLM_KEY is visible to careerclaw.config (import-time constant)
    monkeypatch.setenv("CAREERCLAW_LLM_KEY", "dummy-key")
    import careerclaw.config as cfg
    import importlib
    importlib.reload(cfg)
    monkeypatch.setattr(briefing, "config", cfg)

    # Make enhancer creation succeed but enhance() fail
    monkeypatch.setattr(briefing, "FailoverDraftEnhancer", BoomFailoverEnhancer)

    repo = JsonTrackingRepository(tmp_path)

    result = briefing.run_daily_briefing(
        user_id="test-user",
        profile=_profile(),
        top_k=3,
        repo=repo,
        dry_run=True,
        resume_intel=_resume_intel(),
        no_enhance=False,
    )

    assert len(result.drafts) == 3
    assert all(d.enhanced is False for d in result.drafts)


class ShouldNotBeCreated:
    def __init__(self, *args, **kwargs):
        raise AssertionError("FailoverDraftEnhancer should not be created when no_enhance=True")


def test_no_enhance_flag_forces_deterministic_even_with_key(tmp_path, monkeypatch):
    monkeypatch.setattr(briefing, "fetch_all_jobs", lambda: _fake_jobs())

    # Open LLM gate but force deterministic via flag
    monkeypatch.setattr(briefing.config, "pro_licensed", lambda: True)

    monkeypatch.setenv("CAREERCLAW_LLM_KEY", "dummy-key")
    import careerclaw.config as cfg
    import importlib
    importlib.reload(cfg)
    monkeypatch.setattr(briefing, "config", cfg)

    # Ensure enhancer is not constructed at all
    monkeypatch.setattr(briefing, "FailoverDraftEnhancer", ShouldNotBeCreated)

    repo = JsonTrackingRepository(tmp_path)

    result = briefing.run_daily_briefing(
        user_id="test-user",
        profile=_profile(),
        top_k=3,
        repo=repo,
        dry_run=True,
        resume_intel=_resume_intel(),
        no_enhance=True,
    )

    assert len(result.drafts) == 3
    assert all(d.enhanced is False for d in result.drafts)