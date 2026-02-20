"""
tests/unit/test_config.py

Tests for PR-6 config additions:
- llm_configured() returns False when key is absent
- LLM key does not leak into any structured output fields
"""
import json
import os
import importlib

import pytest


def _reload_config(monkeypatch, key_value):
    """Helper: set env var and reload config so module-level vars pick it up."""
    if key_value is None:
        monkeypatch.delenv("CAREERCLAW_LLM_KEY", raising=False)
    else:
        monkeypatch.setenv("CAREERCLAW_LLM_KEY", key_value)
    import careerclaw.config as cfg
    importlib.reload(cfg)
    return cfg


# ------------------------------------------------------------------
# llm_configured() behaviour
# ------------------------------------------------------------------

def test_llm_configured_false_when_key_absent(monkeypatch):
    cfg = _reload_config(monkeypatch, None)
    assert cfg.llm_configured() is False


def test_llm_configured_false_when_key_empty_string(monkeypatch):
    cfg = _reload_config(monkeypatch, "")
    assert cfg.llm_configured() is False


def test_llm_configured_true_when_key_present(monkeypatch):
    cfg = _reload_config(monkeypatch, "sk-test-key-12345")
    assert cfg.llm_configured() is True


def test_provider_defaults_to_anthropic(monkeypatch):
    monkeypatch.delenv("CAREERCLAW_LLM_PROVIDER", raising=False)
    import careerclaw.config as cfg
    importlib.reload(cfg)
    assert cfg.CAREERCLAW_LLM_PROVIDER == "anthropic"


def test_provider_reads_from_env(monkeypatch):
    monkeypatch.setenv("CAREERCLAW_LLM_PROVIDER", "openai")
    import careerclaw.config as cfg
    importlib.reload(cfg)
    assert cfg.CAREERCLAW_LLM_PROVIDER == "openai"


# ------------------------------------------------------------------
# CAREERCLAW_LLM_MODEL behaviour
# ------------------------------------------------------------------

def test_model_defaults_to_sonnet_for_anthropic(monkeypatch):
    monkeypatch.delenv("CAREERCLAW_LLM_MODEL", raising=False)
    monkeypatch.delenv("CAREERCLAW_LLM_PROVIDER", raising=False)
    import careerclaw.config as cfg
    importlib.reload(cfg)
    assert cfg.CAREERCLAW_LLM_MODEL == "claude-sonnet-4-6"


def test_model_defaults_to_gpt4o_mini_for_openai(monkeypatch):
    monkeypatch.delenv("CAREERCLAW_LLM_MODEL", raising=False)
    monkeypatch.setenv("CAREERCLAW_LLM_PROVIDER", "openai")
    import careerclaw.config as cfg
    importlib.reload(cfg)
    assert cfg.CAREERCLAW_LLM_MODEL == "gpt-4o-mini"


def test_model_reads_from_env(monkeypatch):
    monkeypatch.setenv("CAREERCLAW_LLM_MODEL", "claude-opus-4-6")
    import careerclaw.config as cfg
    importlib.reload(cfg)
    assert cfg.CAREERCLAW_LLM_MODEL == "claude-opus-4-6"


# ------------------------------------------------------------------
# Security: key must not appear in any structured output
# ------------------------------------------------------------------

def test_llm_key_absent_from_briefing_result_dict(monkeypatch):
    """
    The CAREERCLAW_LLM_KEY value must never appear in the JSON-serialisable
    output produced by DailyBriefingResult.to_dict().
    We use a distinctive sentinel value so a simple substring check is reliable.
    """
    sentinel_key = "sk-SECURITY-TEST-SENTINEL-XYZ"
    monkeypatch.setenv("CAREERCLAW_LLM_KEY", sentinel_key)

    # Import after setting env so config picks it up
    from careerclaw.models import UserProfile, NormalizedJob, JobSource
    from careerclaw.briefing import DailyBriefingResult, RankedMatch
    from careerclaw.drafting import DraftResult

    profile = UserProfile(
        skills=["python"],
        target_roles=["engineer"],
        experience_years=5,
        work_mode="remote",
        resume_summary="Engineer.",
    )

    result = DailyBriefingResult(
        user_id="test-user",
        fetched_jobs=1,
        considered_jobs=1,
        top_matches=[],
        drafts=[DraftResult(job_id="abc", draft="Hi team,\n\nTest.", enhanced=False)],
        tracking_created=0,
        tracking_already_present=0,
        duration_ms=100,
        dry_run=True,
        resume_intelligence=None,
    )

    serialised = json.dumps(result.to_dict())
    assert sentinel_key not in serialised, (
        "CAREERCLAW_LLM_KEY value appeared in structured output — security violation."
    )
