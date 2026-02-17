from __future__ import annotations

from datetime import datetime, timezone

from careerclaw.models import NormalizedJob, JobSource, UserProfile
from careerclaw.resume_intel import ResumeIntelligence
from careerclaw.requirements import extract_job_requirements
from careerclaw.gap import analyze_gap


def test_extract_job_requirements_keywords_and_phrases() -> None:
    job = NormalizedJob(
        source=JobSource.REMOTEOK,
        title="Project Manager",
        company="Acme",
        description="Looking for strong project management skills and customer service experience. "
                    "Must handle stakeholder communication and time management.",
        tags=["management", "customer service"],
        posted_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        canonical_url="https://example.com/job/1",
    )
    req = extract_job_requirements(job, max_phrases=20)
    assert "project" in req.keywords
    assert "management" in req.keywords
    # Phrases should include common bigrams/trigrams
    assert any(p in req.phrases for p in ["project management", "customer service", "stakeholder communication"])


def test_gap_analysis_structure_and_fit_score() -> None:
    resume = ResumeIntelligence(
        extracted_keywords=["project", "management", "communication", "python"],
        extracted_phrases=["project management", "stakeholder communication"],
        impact_signals=["20%"],
        source="summary_only",
    )
    job = NormalizedJob(
        source=JobSource.REMOTEOK,
        title="Project Manager",
        company="Acme",
        description="Project management, stakeholder communication, and agile methodology required. "
                    "Nice to have: budget forecasting.",
        posted_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        canonical_url="https://example.com/job/2",
    )
    req = extract_job_requirements(job, max_phrases=30)
    gap = analyze_gap(resume=resume, job=req)
    d = gap.to_dict()
    assert "analysis" in d
    analysis = d["analysis"]
    assert "fit_score" in analysis
    assert "signals" in analysis and "gaps" in analysis

    # Keywords and phrases separated
    assert "keywords" in analysis["signals"]
    assert "phrases" in analysis["signals"]
    assert "keywords" in analysis["gaps"]
    assert "phrases" in analysis["gaps"]

    # Some expected matches
    assert "project management" in analysis["signals"]["phrases"]
    assert "stakeholder communication" in analysis["signals"]["phrases"]
    # Some expected gaps (phrase)
    assert "agile methodology" in analysis["gaps"]["phrases"]
