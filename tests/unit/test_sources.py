from careerclaw import sources
from careerclaw.models import JobSource, NormalizedJob

from datetime import datetime, timezone


def _one_job() -> list[NormalizedJob]:
    return [
        NormalizedJob(
            source=JobSource.REMOTEOK,
            title="Engineer",
            company="TestCo",
            description="Python",
            posted_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            canonical_url="https://example.com/1",
        )
    ]


def test_fetch_all_jobs_survives_one_source_failure(monkeypatch):
    monkeypatch.setattr(sources, "fetch_remoteok_jobs", lambda: (_ for _ in ()).throw(RuntimeError("timeout")))
    monkeypatch.setattr(sources, "fetch_hn_whos_hiring_jobs_default", _one_job)

    jobs = sources.fetch_all_jobs()
    assert len(jobs) == 1


def test_fetch_all_jobs_raises_when_all_fail(monkeypatch):
    monkeypatch.setattr(sources, "fetch_remoteok_jobs", lambda: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(sources, "fetch_hn_whos_hiring_jobs_default", lambda: (_ for _ in ()).throw(RuntimeError("down")))

    try:
        sources.fetch_all_jobs()
        assert False, "Should have raised"
    except RuntimeError as exc:
        assert "All sources failed" in str(exc)

