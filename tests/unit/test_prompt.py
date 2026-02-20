"""
tests/unit/test_prompt.py

Tests for careerclaw/llm/prompt.py:
- Prompt contains job title and company name
- Prompt contains >=2 matched signal tokens
- Total prompt token estimate < 600
"""
import pytest

from careerclaw.gap import GapAnalysis
from careerclaw.llm.prompt import build_enhance_prompt, estimate_token_count, _SYSTEM_PROMPT
from careerclaw.models import NormalizedJob, JobSource
from careerclaw.resume_intel import ResumeIntelligence


def _make_job(title="Senior Engineer", company="Acme", description="Acme builds developer tools."):
    return NormalizedJob(
        source=JobSource.HN_WHO_IS_HIRING,
        title=title,
        company=company,
        description=description,
        location="Remote",
        tags=[],
        posted_at=None,
        canonical_url="https://example.com",
        source_ref="12345",
    )


def _make_resume(keywords=None, phrases=None, kw_stream=None):
    keywords = keywords or ["python", "react", "senior", "engineer"]
    phrases = phrases or ["senior engineer", "react python"]
    kw_stream = kw_stream or keywords
    weights = {k: 1.0 for k in keywords}
    ph_weights = {p: 1.0 for p in phrases}
    return ResumeIntelligence(
        extracted_keywords=keywords,
        extracted_phrases=phrases,
        keyword_stream=kw_stream,
        phrase_stream=phrases,
        impact_signals=[],
        keyword_weights=weights,
        phrase_weights=ph_weights,
        source="skills_injected",
    )


def _make_gap(matched_kw=None, matched_ph=None, missing_kw=None, missing_ph=None):
    return GapAnalysis(
        matched_keywords=matched_kw or ["python", "react"],
        missing_keywords=missing_kw or ["kotlin"],
        matched_phrases=matched_ph or ["senior engineer"],
        missing_phrases=missing_ph or [],
        fit_score=0.45,
        fit_score_unweighted=0.38,
    )


# ------------------------------------------------------------------
# Content requirements
# ------------------------------------------------------------------

def test_prompt_contains_job_title():
    job = _make_job(title="Staff Backend Engineer")
    prompt = build_enhance_prompt(job=job, resume=_make_resume(), gap=_make_gap())
    assert "Staff Backend Engineer" in prompt


def test_prompt_contains_company_name():
    job = _make_job(company="Starbridge")
    prompt = build_enhance_prompt(job=job, resume=_make_resume(), gap=_make_gap())
    assert "Starbridge" in prompt


def test_prompt_contains_at_least_two_matched_signals():
    gap = _make_gap(matched_kw=["python", "react", "typescript"], matched_ph=["senior engineer"])
    prompt = build_enhance_prompt(job=_make_job(), resume=_make_resume(), gap=gap)
    # At least 2 of the matched signals must appear verbatim in the prompt
    signals = gap.matched_keywords + gap.matched_phrases
    found = [s for s in signals if s in prompt]
    assert len(found) >= 2, f"Only {len(found)} signal(s) found in prompt: {found}"


def test_prompt_contains_company_context_from_description():
    job = _make_job(description="Acme builds the fastest data pipeline on earth. We are hiring.")
    prompt = build_enhance_prompt(job=job, resume=_make_resume(), gap=_make_gap())
    assert "Acme builds" in prompt


def test_system_prompt_plus_user_prompt_under_600_tokens():
    job = _make_job(
        title="Senior Software Engineer",
        company="Starbridge",
        description="Starbridge is building an AI platform for enterprise sales intelligence.",
    )
    gap = _make_gap(
        matched_kw=["python", "react", "typescript", "aws", "reliability"],
        matched_ph=["senior engineer", "software engineer"],
    )
    resume = _make_resume(
        keywords=["python", "react", "typescript", "aws", "reliability", "senior", "engineer"],
        phrases=["senior engineer"],
    )
    user_prompt = build_enhance_prompt(job=job, resume=resume, gap=gap)
    total_tokens = estimate_token_count(_SYSTEM_PROMPT) + estimate_token_count(user_prompt)
    assert total_tokens < 600, f"Token estimate {total_tokens} exceeds 600 budget"


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------

def test_prompt_handles_empty_gap_signals_gracefully():
    gap = _make_gap(matched_kw=[], matched_ph=[])
    prompt = build_enhance_prompt(job=_make_job(), resume=_make_resume(), gap=gap)
    assert "none detected" in prompt.lower() or len(prompt) > 100


def test_prompt_handles_missing_company_gracefully():
    job = _make_job(company=None, description="We build great things.")
    prompt = build_enhance_prompt(job=job, resume=_make_resume(), gap=_make_gap())
    assert len(prompt) > 100  # produced something


def test_prompt_description_capped_at_150_chars():
    long_desc = "X" * 300 + "."
    job = _make_job(description=long_desc)
    prompt = build_enhance_prompt(job=job, resume=_make_resume(), gap=_make_gap())
    # The context line should not contain 300 X's verbatim
    assert "X" * 300 not in prompt
