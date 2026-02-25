import os

from careerclaw.config import load_llm_failover_config


def test_load_llm_failover_config_parses_chain(monkeypatch):
    monkeypatch.setenv(
        "CAREERCLAW_LLM_CHAIN",
        "openai/gpt-5.2, openai/gpt-4o-mini ,anthropic/claude-sonnet-4-6",
    )
    monkeypatch.setenv("CAREERCLAW_LLM_MAX_RETRIES", "3")
    monkeypatch.setenv("CAREERCLAW_LLM_CIRCUIT_BREAKER_FAILS", "5")

    cfg = load_llm_failover_config()

    assert cfg.chain == [
        ("openai", "gpt-5.2"),
        ("openai", "gpt-4o-mini"),
        ("anthropic", "claude-sonnet-4-6"),
    ]
    assert cfg.max_retries == 3
    assert cfg.breaker_consecutive_fails == 5


def test_load_llm_failover_config_allows_openai_model_shorthand(monkeypatch):
    # If someone uses shorthand without provider, assume openai
    monkeypatch.setenv("CAREERCLAW_LLM_CHAIN", "gpt-5.2,anthropic/claude-sonnet-4-6")

    cfg = load_llm_failover_config()

    assert cfg.chain[0] == ("openai", "gpt-5.2")
    assert cfg.chain[1] == ("anthropic", "claude-sonnet-4-6")