"""
tests/unit/test_llm_enhancer.py

Tests for LLMDraftEnhancer — all LLM calls are mocked.
No network, no API keys required.
"""
import pytest
from unittest.mock import MagicMock, patch

from careerclaw.gap import GapAnalysis
from careerclaw.llm.enhancer import DraftEnhancerError, LLMDraftEnhancer
from careerclaw.models import NormalizedJob, JobSource
from careerclaw.resume_intel import ResumeIntelligence


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

def _make_resume():
    return ResumeIntelligence(
        extracted_keywords=["python", "react", "senior", "engineer"],
        extracted_phrases=["senior engineer"],
        keyword_stream=["python", "react", "senior", "engineer"],
        phrase_stream=["senior engineer"],
        impact_signals=[],
        keyword_weights={"python": 1.0, "react": 1.0, "senior": 1.0, "engineer": 1.0},
        phrase_weights={"senior engineer": 1.0},
        source="skills_injected",
    )


def _make_gap():
    return GapAnalysis(
        matched_keywords=["python", "react"],
        missing_keywords=["kotlin"],
        matched_phrases=["senior engineer"],
        missing_phrases=[],
        fit_score=0.45,
        fit_score_unweighted=0.38,
    )


def _make_job():
    return NormalizedJob(
        source=JobSource.HN_WHO_IS_HIRING,
        title="Senior Engineer",
        company="Acme",
        description="Acme builds developer tools. We need a senior engineer.",
        location="Remote",
        tags=[],
        posted_at=None,
        canonical_url="https://example.com",
        source_ref="99999",
    )


def _valid_enhanced_text():
    """100-word body that passes word-count validation."""
    return (
        "Hi Acme team, I am writing regarding the Senior Engineer position. "
        "My background includes extensive Python and React experience, which aligns directly "
        "with your stack. As a senior engineer I have shipped production systems handling "
        "large-scale data pipelines and built developer tooling adopted across multiple teams. "
        "At my previous role I led the migration of a core service to a microservices "
        "architecture, reducing latency by 40 percent. I would welcome the opportunity "
        "to discuss how my experience maps to your current roadmap. Please feel free to "
        "reach out at your convenience."
    )


# ------------------------------------------------------------------
# Anthropic path
# ------------------------------------------------------------------

def test_anthropic_enhancer_returns_text(monkeypatch):
    enhanced_body = _valid_enhanced_text()

    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = enhanced_body

    mock_message = MagicMock()
    mock_message.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("careerclaw.llm.enhancer.anthropic") as mock_anthropic:
        mock_anthropic.Anthropic.return_value = mock_client
        mock_anthropic.APITimeoutError = Exception
        mock_anthropic.APIError = Exception

        enhancer = LLMDraftEnhancer(
            api_key="sk-fake",
            provider="anthropic",
            resume=_make_resume(),
        )
        result = enhancer.enhance(job=_make_job(), gap=_make_gap())

    assert result == enhanced_body
    mock_client.messages.create.assert_called_once()


def test_anthropic_timeout_raises_enhancer_error(monkeypatch):
    class FakeTimeoutError(Exception):
        pass

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = FakeTimeoutError("timeout")

    with patch("careerclaw.llm.enhancer.anthropic") as mock_anthropic:
        mock_anthropic.Anthropic.return_value = mock_client
        mock_anthropic.APITimeoutError = FakeTimeoutError
        mock_anthropic.APIError = Exception

        enhancer = LLMDraftEnhancer(
            api_key="sk-fake",
            provider="anthropic",
            resume=_make_resume(),
        )
        with pytest.raises(DraftEnhancerError, match="timed out"):
            enhancer.enhance(job=_make_job(), gap=_make_gap())


# ------------------------------------------------------------------
# OpenAI path
# ------------------------------------------------------------------

def test_openai_enhancer_returns_text():
    enhanced_body = _valid_enhanced_text()

    mock_choice = MagicMock()
    mock_choice.message.content = enhanced_body

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("careerclaw.llm.enhancer.openai") as mock_openai:
        mock_openai.OpenAI.return_value = mock_client
        mock_openai.APITimeoutError = Exception
        mock_openai.APIError = Exception

        enhancer = LLMDraftEnhancer(
            api_key="sk-openai-fake",
            provider="openai",
            resume=_make_resume(),
        )
        result = enhancer.enhance(job=_make_job(), gap=_make_gap())

    assert result == enhanced_body


def test_openai_timeout_raises_enhancer_error():
    class FakeTimeoutError(Exception):
        pass

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = FakeTimeoutError("timeout")

    with patch("careerclaw.llm.enhancer.openai") as mock_openai:
        mock_openai.OpenAI.return_value = mock_client
        mock_openai.APITimeoutError = FakeTimeoutError
        mock_openai.APIError = Exception

        enhancer = LLMDraftEnhancer(
            api_key="sk-openai-fake",
            provider="openai",
            resume=_make_resume(),
        )
        with pytest.raises(DraftEnhancerError, match="timed out"):
            enhancer.enhance(job=_make_job(), gap=_make_gap())


# ------------------------------------------------------------------
# Output validation
# ------------------------------------------------------------------

def test_output_too_short_raises_enhancer_error():
    short_text = "Too short."  # < 50 words

    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = short_text

    mock_message = MagicMock()
    mock_message.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("careerclaw.llm.enhancer.anthropic") as mock_anthropic:
        mock_anthropic.Anthropic.return_value = mock_client
        mock_anthropic.APITimeoutError = Exception
        mock_anthropic.APIError = Exception

        enhancer = LLMDraftEnhancer(
            api_key="sk-fake",
            provider="anthropic",
            resume=_make_resume(),
        )
        with pytest.raises(DraftEnhancerError, match="too short"):
            enhancer.enhance(job=_make_job(), gap=_make_gap())


def test_output_too_long_raises_enhancer_error():
    long_text = " ".join(["word"] * 400)  # > 350 words

    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = long_text

    mock_message = MagicMock()
    mock_message.content = [mock_block]

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("careerclaw.llm.enhancer.anthropic") as mock_anthropic:
        mock_anthropic.Anthropic.return_value = mock_client
        mock_anthropic.APITimeoutError = Exception
        mock_anthropic.APIError = Exception

        enhancer = LLMDraftEnhancer(
            api_key="sk-fake",
            provider="anthropic",
            resume=_make_resume(),
        )
        with pytest.raises(DraftEnhancerError, match="too long"):
            enhancer.enhance(job=_make_job(), gap=_make_gap())


def test_empty_api_key_raises_enhancer_error():
    with pytest.raises(DraftEnhancerError, match="must not be empty"):
        LLMDraftEnhancer(api_key="", provider="anthropic", resume=_make_resume())


def test_unsupported_provider_raises_enhancer_error():
    with pytest.raises(DraftEnhancerError, match="Unsupported provider"):
        LLMDraftEnhancer(api_key="sk-fake", provider="gemini", resume=_make_resume())


def test_empty_response_raises_enhancer_error():
    mock_message = MagicMock()
    mock_message.content = []  # no blocks

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message

    with patch("careerclaw.llm.enhancer.anthropic") as mock_anthropic:
        mock_anthropic.Anthropic.return_value = mock_client
        mock_anthropic.APITimeoutError = Exception
        mock_anthropic.APIError = Exception

        enhancer = LLMDraftEnhancer(
            api_key="sk-fake",
            provider="anthropic",
            resume=_make_resume(),
        )
        with pytest.raises(DraftEnhancerError, match="no text content"):
            enhancer.enhance(job=_make_job(), gap=_make_gap())
