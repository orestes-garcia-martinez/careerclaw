import json
from pathlib import Path
from datetime import timezone

import pytest

from careerclaw.models import NormalizedJob, JobSource
from careerclaw.adapters import remoteok as remoteok_adapter
from careerclaw.adapters import hackernews as hn_adapter


def assert_normalized_job_contract(job: NormalizedJob) -> None:
    """
    A reusable 'contract' assertion:
    Any adapter output must satisfy these invariants.

    If this function fails, your adapter is not producing the canonical shape.
    """
    assert isinstance(job, NormalizedJob)

    # Required fields must be non-empty strings (NormalizedJob.__post_init__ normalizes whitespace)
    assert isinstance(job.title, str) and job.title.strip()
    assert isinstance(job.company, str) and job.company.strip()
    assert isinstance(job.description, str) and job.description.strip()

    # Source must be one of the enum values
    assert job.source in (JobSource.REMOTEOK, JobSource.HN_WHO_IS_HIRING)

    # job_id should be present and stable-sized (models.py uses sha256 and slices to 16 chars)
    assert isinstance(job.job_id, str)
    assert len(job.job_id) == 16

    # tags should be a list; each tag is normalized to lowercase and unique in NormalizedJob
    assert isinstance(job.tags, list)
    for t in job.tags:
        assert t == t.lower()
        assert t.strip()

    # posted_at if present should be timezone-aware UTC per your models normalization
    if job.posted_at is not None:
        assert job.posted_at.tzinfo is not None
        # We accept any tz-aware, but you generally normalize to UTC
        assert job.posted_at.tzinfo == timezone.utc


# ---------- RemoteOK: Contract Test (offline, deterministic) ----------

def test_remoteok_adapter_parses_rss_fixture(monkeypatch, load_text):
    """
    Goal:
    - Teach: monkeypatch a network function to return fixture content.
    - Validate: RemoteOK adapter converts RSS XML -> List[NormalizedJob].

    Logic:
    1) Load remoteok_sample.xml from tests/fixtures
    2) Patch remoteok._fetch_text so it returns this XML string (no network)
    3) Call fetch_remoteok_jobs()
    4) Assert jobs list is non-empty and each job satisfies NormalizedJob contract
    5) Spot-check: tags are parsed; location inference works for known tags.
    """
    xml = load_text("remoteok_sample.xml")

    def fake_fetch_text(url: str, timeout_seconds: int = 0) -> str:
        return xml

    # Patch the adapter's network fetch function
    monkeypatch.setattr(remoteok_adapter, "_fetch_text", fake_fetch_text)

    jobs = remoteok_adapter.fetch_remoteok_jobs(rss_url="https://example.test/rss", limit=10)
    assert len(jobs) == 2

    for j in jobs:
        assert_normalized_job_contract(j)
        assert j.source == JobSource.REMOTEOK

    # Spot checks to ensure mapping is correct
    first = jobs[0]
    assert "Frontend" in first.title or "Backend" in first.title

    # One of the items includes "usa" tag -> inferred location "USA"
    # The other includes "worldwide" -> inferred "Worldwide"
    locations = {j.location for j in jobs}
    assert "USA" in locations
    assert "Worldwide" in locations


# ---------- Hacker News: Contract Test (offline, deterministic) ----------

def test_hn_adapter_parses_thread_and_comments_fixtures(monkeypatch,load_json):
    """
    Goal:
    - Teach: patch _hn_item to return deterministic JSON for thread + comments.
    - Validate: HN adapter produces NormalizedJob per top-level comments.

    Logic:
    1) Load hn_thread.json + comment fixtures
    2) Patch hackernews._hn_item so when called with item_id it returns the right fixture
    3) Call fetch_hn_whos_hiring_jobs(thread_id)
    4) Validate: two jobs returned, correct source, canonical_url built, description stripped/normalized
    """
    thread = load_json("hn_thread.json")
    c1 = load_json("hn_comment_1.json")
    c2 = load_json("hn_comment_2.json")

    # Map item id -> fixture
    items = {
        thread["id"]: thread,
        c1["id"]: c1,
        c2["id"]: c2,
    }

    def fake_hn_item(item_id: int) -> dict:
        return items[int(item_id)]

    monkeypatch.setattr(hn_adapter, "_hn_item", fake_hn_item)

    jobs = hn_adapter.fetch_hn_whos_hiring_jobs(whos_hiring_thread_id=thread["id"], limit_comments=10)
    assert len(jobs) == 2

    for j in jobs:
        assert_normalized_job_contract(j)
        assert j.source == JobSource.HN_WHO_IS_HIRING
        assert j.canonical_url is not None
        assert "news.ycombinator.com/item?id=" in j.canonical_url

        # Ensure HTML was stripped from description (no tags should remain)
        assert "<" not in j.description
        assert ">" not in j.description

    # Spot check: best-effort header parsing sets company/title and location-ish segment
    # Because our comment header uses "Company | Location | Role"
    j_titles = [j.title.lower() for j in jobs]
    assert any("frontend" in t for t in j_titles) or any("backend" in t for t in j_titles)

    companies = {j.company for j in jobs}
    assert "Acme Corp" in companies
    assert "Beta Systems" in companies

    locations = {j.location for j in jobs}
    assert any("Remote" in (loc or "") for loc in locations)
    assert any("Jacksonville" in (loc or "") for loc in locations)


def test_hn_adapter_skips_deleted_or_dead_comments(monkeypatch,load_json):
    """
    Goal:
    - Teach: testing edge cases by modifying fixtures.
    - Validate: adapter skips deleted/dead comments as intended.

    Logic:
    1) Start with the same thread fixture
    2) Make one comment 'deleted': true
    3) Ensure only the other comment produces a job
    """
    thread = load_json("hn_thread.json")
    c1 = load_json("hn_comment_1.json")
    c2 = load_json("hn_comment_2.json")

    c2_deleted = dict(c2)
    c2_deleted["deleted"] = True

    items = {
        thread["id"]: thread,
        c1["id"]: c1,
        c2_deleted["id"]: c2_deleted,
    }

    def fake_hn_item(item_id: int) -> dict:
        return items[int(item_id)]

    monkeypatch.setattr(hn_adapter, "_hn_item", fake_hn_item)

    jobs = hn_adapter.fetch_hn_whos_hiring_jobs(whos_hiring_thread_id=thread["id"], limit_comments=10)
    assert len(jobs) == 1
    assert jobs[0].company == "Acme Corp"

