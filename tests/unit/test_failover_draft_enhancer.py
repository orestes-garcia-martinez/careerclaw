import pytest

import careerclaw.llm.enhancer as enh


class _AlwaysFailEnhancer:
    """
    Stand-in for LLMDraftEnhancer that always fails.
    FailoverDraftEnhancer instantiates LLMDraftEnhancer from the module, so
    we monkeypatch enh.LLMDraftEnhancer to this class in tests.
    """

    def __init__(self, *args, **kwargs):
        pass

    def enhance(self, *args, **kwargs):
        raise enh.DraftEnhancerError("boom")


def test_failover_circuit_breaker_trips_after_n_consecutive_failures(monkeypatch):
    # Patch LLMDraftEnhancer used internally by FailoverDraftEnhancer
    monkeypatch.setattr(enh, "LLMDraftEnhancer", _AlwaysFailEnhancer)

    # No sleeping during tests even if retry/backoff exists
    if hasattr(enh, "_sleep_backoff"):
        monkeypatch.setattr(enh, "_sleep_backoff", lambda attempt: None)

    f = enh.FailoverDraftEnhancer(
        api_key_resolver=lambda provider: "dummy",
        candidates=[
            ("openai", "gpt-5.2"),
            ("openai", "gpt-4o-mini"),
            ("anthropic", "claude-sonnet-4-6"),
        ],
        resume=None,  # your wrapper stores it; it's fine for this stub
        max_retries=0,  # keep the test deterministic
        breaker_consecutive_fails=2,  # trip quickly
    )

    # First call: tries candidates until it accumulates failures
    with pytest.raises(enh.DraftEnhancerError):
        f.enhance(job=None, gap=None)

    # Second call: should trip circuit breaker and raise immediately
    with pytest.raises(RuntimeError) as e:
        f.enhance(job=None, gap=None)

    assert "disabled" in str(e.value).lower() or "circuit" in str(e.value).lower()
    assert f.is_disabled() is True