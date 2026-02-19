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


def test_briefing_falls_back_to_deterministic_when_enhancer_raises(tmp_path, monkeypatch):
    """If LLMDraftEnhancer.enhance() raises, briefing must fall back silently."""
    monkeypatch.setenv("CAREERCLAW_LLM_KEY", "sk-fake-key")
    monkeypatch.setattr(briefing, "fetch_all_jobs", lambda: _fake_jobs())

    import careerclaw.config as cfg
    import importlib
    importlib.reload(cfg)
    monkeypatch.setattr(briefing, "config", cfg)

    # Patch LLMDraftEnhancer so enhance() always raises
    mock_enhancer_instance = MagicMock()
    mock_enhancer_instance.enhance.side_effect = DraftEnhancerError("Simulated failure")

    with patch("careerclaw.briefing.LLMDraftEnhancer", return_value=mock_enhancer_instance):
        result = briefing.run_daily_briefing(
            user_id="test-user",
            profile=_profile(),
            top_k=3,
            dry_run=True,
            resume_intel=_resume_intel(),
        )

    # All drafts should be deterministic (enhanced=False)
    d = result.to_dict()
    for draft in d["drafts"]:
        assert draft["enhanced"] is False

    # And briefing must have produced results despite the failure
    assert len(d["drafts"]) == 3


def test_no_enhance_flag_forces_deterministic_even_with_key(tmp_path, monkeypatch):
    """--no-enhance must prevent LLM calls even when CAREERCLAW_LLM_KEY is set."""
    monkeypatch.setenv("CAREERCLAW_LLM_KEY", "sk-fake-key")
    monkeypatch.setattr(briefing, "fetch_all_jobs", lambda: _fake_jobs())

    import careerclaw.config as cfg
    import importlib
    importlib.reload(cfg)
    monkeypatch.setattr(briefing, "config", cfg)

    mock_enhancer_instance = MagicMock()

    with patch("careerclaw.briefing.LLMDraftEnhancer", return_value=mock_enhancer_instance) as mock_cls:
        result = briefing.run_daily_briefing(
            user_id="test-user",
            profile=_profile(),
            top_k=3,
            dry_run=True,
            resume_intel=_resume_intel(),
            no_enhance=True,
        )

    # Enhancer should never have been instantiated
    mock_cls.assert_not_called()

    d = result.to_dict()
    for draft in d["drafts"]:
        assert draft["enhanced"] is False
