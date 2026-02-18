from __future__ import annotations

from datetime import datetime, timezone

from careerclaw.models import NormalizedJob, JobSource
from careerclaw.resume_intel import build_resume_intelligence
from careerclaw.requirements import extract_job_requirements
from careerclaw.gap import analyze_gap


def test_extract_job_requirements_includes_ordered_keyword_stream() -> None:
    job = NormalizedJob(
        source=JobSource.REMOTEOK,
        title="Customer Support Specialist",
        company="Acme",
        description="We need customer service experience, phone support, and time management. "
                    "Great communication and problem solving are required.",
        tags=["customer service", "support"],
        posted_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        canonical_url="https://example.com/job/1",
    )
    req = extract_job_requirements(job, max_phrases=20)
    assert req.keyword_stream, "keyword_stream should be populated"
    # first-seen ordering should reflect the job text
    assert req.keyword_stream[0] in {"customer", "support", "specialist"}  # title tokens appear early
    assert "customer service" in req.phrases


def test_gap_analysis_structure_ordering_and_summary() -> None:
    resume = build_resume_intelligence(
        resume_summary="Experienced in customer service and phone support.",
        resume_text="",
    )
    job = NormalizedJob(
        source=JobSource.REMOTEOK,
        title="Customer Support Specialist",
        company="Acme",
        description="customer service and phone support required. nice to have: time management and data entry.",
        posted_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        canonical_url="https://example.com/job/2",
    )
    req = extract_job_requirements(job, max_phrases=30)
    gap = analyze_gap(resume=resume, job=req)
    d = gap.to_dict()
    analysis = d["analysis"]

    # keywords and phrases separated
    assert "signals" in analysis and "gaps" in analysis
    assert "keywords" in analysis["signals"] and "phrases" in analysis["signals"]
    assert "keywords" in analysis["gaps"] and "phrases" in analysis["gaps"]

    # contains summary for readable preview
    assert "summary" in analysis
    assert "top_signals" in analysis["summary"]
    assert "top_gaps" in analysis["summary"]

    # ordering: job order should be preserved for phrases
    sig_ph = analysis["signals"]["phrases"]
    gap_ph = analysis["gaps"]["phrases"]
    # "customer service" appears before "phone support" in the description string
    if "customer service" in sig_ph and "phone support" in sig_ph:
        assert sig_ph.index("customer service") < sig_ph.index("phone support")


def test_section_weighting_affects_fit_score() -> None:
    resume = build_resume_intelligence(
        resume_summary="",
        resume_text="""SKILLS
customer service
phone support

INTERESTS
data entry
""",
    )
    job = NormalizedJob(
        source=JobSource.REMOTEOK,
        title="Customer Support Specialist",
        company="Acme",
        description="customer service phone support data entry",
        posted_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
        canonical_url="https://example.com/job/3",
    )
    req = extract_job_requirements(job, max_phrases=10)
    gap = analyze_gap(resume=resume, job=req)

    # Section weighting: skills are weighted higher than interests; fit_score should be <= unweighted
    assert gap.fit_score <= gap.fit_score_unweighted + 1e-9
    # And should still be non-zero
    assert gap.fit_score > 0.0
