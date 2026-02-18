from __future__ import annotations

from pathlib import Path

from careerclaw.resume_intel import build_resume_intelligence
from careerclaw.io.resume_loader import load_resume_text


def test_resume_text_loader_and_intel_extracts_keywords_phrases_and_impacts() -> None:
    txt = "Led customer service operations. Increased satisfaction by 25%. Managed scheduling and training."
    loaded = load_resume_text(resume_text_path=str(_fixture_txt()), resume_pdf_path=None)
    assert loaded.source == "text"
    intel = build_resume_intelligence(resume_summary="Operations lead", resume_text=loaded.text)

    # keyword presence (domain-agnostic)
    assert "customer" in intel.extracted_keywords
    assert "service" in intel.extracted_keywords

    # phrase extraction (bigrams)
    assert any(p in intel.extracted_phrases for p in ["customer service", "service operations"])

    # impact signals
    assert "25%" in intel.impact_signals


def test_resume_pdf_loader_best_effort() -> None:
    loaded = load_resume_text(resume_text_path=None, resume_pdf_path=str(_fixture_pdf()))
    # We don't assert exact text because PDF extraction varies, but it should not crash
    assert loaded.path is not None
    assert loaded.source in {"pdf", "none"}


# ---------------------------------------------------------------------------
# Phase-5E: skills + target_roles injection
# ---------------------------------------------------------------------------

def test_profile_skills_appear_in_extracted_keywords() -> None:
    """UserProfile.skills must appear in extracted_keywords with weight 1.0."""
    intel = build_resume_intelligence(
        resume_summary="Backend engineer.",
        resume_text="",
        skills=["python", "react", "typescript"],
    )
    assert "python" in intel.extracted_keywords
    assert "react" in intel.extracted_keywords
    assert "typescript" in intel.extracted_keywords


def test_profile_skills_have_weight_1_0() -> None:
    """Skills section has the highest weight; tokens must be weighted 1.0."""
    intel = build_resume_intelligence(
        resume_summary="",
        resume_text="",
        skills=["python", "kubernetes"],
    )
    assert intel.keyword_weights.get("python") == 1.0
    assert intel.keyword_weights.get("kubernetes") == 1.0


def test_target_roles_appear_in_extracted_keywords() -> None:
    """UserProfile.target_roles tokens must also be extracted."""
    intel = build_resume_intelligence(
        resume_summary="",
        resume_text="",
        target_roles=["frontend engineer", "software engineer"],
    )
    assert "frontend" in intel.extracted_keywords
    assert "engineer" in intel.extracted_keywords
    assert "software" in intel.extracted_keywords


def test_skills_are_not_in_gap_missing_keywords() -> None:
    """Skills listed in profile must NOT appear as missing keywords in GapAnalysis."""
    from careerclaw.gap import analyze_gap
    from careerclaw.requirements import extract_job_requirements
    from careerclaw.models import NormalizedJob, JobSource

    intel = build_resume_intelligence(
        resume_summary="Senior engineer.",
        resume_text="",
        skills=["python", "react", "typescript", "aws"],
    )
    job = NormalizedJob(
        source=JobSource.HN_WHO_IS_HIRING,
        title="Senior Engineer",
        company="Acme",
        description="We use Python and React. TypeScript required. AWS experience a plus.",
        location="Remote",
        tags=[],
        posted_at=None,
        canonical_url="https://example.com",
        source_ref="1",
    )
    reqs = extract_job_requirements(job)
    gap = analyze_gap(resume=intel, job=reqs)

    # Profile skills should be signals, not gaps
    assert "python" not in gap.missing_keywords
    assert "react" not in gap.missing_keywords
    assert "typescript" not in gap.missing_keywords


def test_empty_skills_does_not_break_build() -> None:
    """Empty skills and target_roles must not raise and must produce valid output."""
    intel = build_resume_intelligence(
        resume_summary="Engineer.",
        resume_text="",
        skills=[],
        target_roles=[],
    )
    assert isinstance(intel.extracted_keywords, list)
    assert isinstance(intel.keyword_weights, dict)


def test_fit_score_improves_with_skills_injection() -> None:
    """Fit score must be higher when profile skills overlap with job than without."""
    from careerclaw.gap import analyze_gap
    from careerclaw.requirements import extract_job_requirements
    from careerclaw.models import NormalizedJob, JobSource

    job = NormalizedJob(
        source=JobSource.HN_WHO_IS_HIRING,
        title="Python Engineer",
        company="Acme",
        description="Python, React, TypeScript, AWS, observability required.",
        location="Remote",
        tags=[],
        posted_at=None,
        canonical_url="https://example.com",
        source_ref="2",
    )
    reqs = extract_job_requirements(job)

    intel_without = build_resume_intelligence(
        resume_summary="Senior engineer focused on systems thinking and reliability.",
        resume_text="",
    )
    intel_with = build_resume_intelligence(
        resume_summary="Senior engineer focused on systems thinking and reliability.",
        resume_text="",
        skills=["python", "react", "typescript", "aws", "observability"],
    )

    gap_without = analyze_gap(resume=intel_without, job=reqs)
    gap_with = analyze_gap(resume=intel_with, job=reqs)

    assert gap_with.fit_score > gap_without.fit_score, (
        f"Expected fit_score to improve with skills injection: "
        f"without={gap_without.fit_score}, with={gap_with.fit_score}"
    )


def _fixture_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures"


def _fixture_txt() -> Path:
    return _fixture_dir() / "resume_fixture.txt"


def _fixture_pdf() -> Path:
    return _fixture_dir() / "resume_fixture.pdf"
