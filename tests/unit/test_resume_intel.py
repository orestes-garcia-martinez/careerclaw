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


def _fixture_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures"


def _fixture_txt() -> Path:
    return _fixture_dir() / "resume_fixture.txt"


def _fixture_pdf() -> Path:
    return _fixture_dir() / "resume_fixture.pdf"
