"""
tests/unit/test_hn_header_parsing.py

Unit tests for _best_effort_parse_header URL stripping fixes.
Covers the bug where HN posts starting with a URL (e.g. "https://doowii.io Doowii | ...")
polluted both the company name and the job title.
"""
import pytest
from careerclaw.adapters.hackernews import _best_effort_parse_header


def test_url_stripped_from_company():
    """URL prefix in first pipe segment must not appear in company name."""
    text = "https://doowii.io Doowii | Remote (US) | Full-time | Senior Software Engineer (AI)"
    title, company, location = _best_effort_parse_header(text)
    assert "http" not in company
    assert "doowii.io" not in company
    assert company == "Doowii"


def test_url_stripped_from_title():
    """URL prefix in role segment must not appear in title."""
    text = "Doowii | Remote (US) | https://doowii.io Senior Software Engineer (AI)"
    title, company, location = _best_effort_parse_header(text)
    assert "http" not in title
    assert title.startswith("Senior Software Engineer")


def test_clean_post_unaffected():
    """Standard clean HN format must parse correctly after the fix."""
    text = "Starbridge | Senior Engineers (Kotlin/Java/React/Typescript) | NYC or Remote | Full-time"
    title, company, location = _best_effort_parse_header(text)
    assert company == "Starbridge"
    assert "http" not in title
    assert title  # non-empty


def test_url_only_company_falls_back_gracefully():
    """If the company segment is only a URL, result should not be the raw URL."""
    text = "https://example.com | Senior Engineer | Remote"
    title, company, location = _best_effort_parse_header(text)
    # After URL stripping, company segment becomes empty — should fall back, not crash
    assert "http" not in company


def test_description_not_picked_as_title():
    """Long description text after URL stripping must not be used as title.
    
    Doowii's actual HN post format: the 4th segment after URL-strip becomes the
    company description ('Doowii is building an AI operating layer...'), which
    contains role keywords like 'ai' and 'platform'. It must not be used as title.
    """
    text = (
        "Doowii | Remote (US) | Full-time | https://doowii.io "
        "Doowii is building an AI operating layer for education analytics: "
        "connect your institution's systems (SIS/LMS/CRM), and non-technical teams "
        "can ask questions, explore, and take action with integrated workflows"
    )
    title, company, location = _best_effort_parse_header(text)
    # Title should fall back to "Hiring", not the description sentence
    assert len(title) <= 80, f"Title too long (likely description): {title!r}"
    assert "is building" not in title
