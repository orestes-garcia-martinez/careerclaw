"""
careerclaw/llm/enhancer.py

DraftEnhancer protocol + LLMDraftEnhancer implementation.

Design principles (PR-6):
- User-provided API key only (no backend dependency)
- Single LLM call per draft, ~450 tokens input
- 10-second hard timeout
- Word-count validation (50-350 words)
- Graceful degradation: raises DraftEnhancerError on any failure
  (caller is responsible for falling back to deterministic draft)
- API key MUST NOT appear in any log or structured output
"""
from __future__ import annotations

import textwrap
import random
import time

from dataclasses import dataclass
from typing import Optional, Tuple, Callable

from typing import Optional

from careerclaw.gap import GapAnalysis
from careerclaw.llm.prompt import _SYSTEM_PROMPT, build_enhance_prompt
from careerclaw.models import NormalizedJob, UserProfile
from careerclaw.resume_intel import ResumeIntelligence
from careerclaw import config as _config

TRANSIENT_HINTS = (
    "rate limit",
    "ratelimit",
    "too many requests",
    "overloaded",
    "temporarily overloaded",
    "timeout",
    "timed out",
    "try again",
    "server error",
    "503",
    "529",
)

# Top-level optional imports so tests can patch them via module attribute.
# The actual ImportError (if library not installed) is raised at call time.
try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore[assignment]

try:
    import openai
except ImportError:
    openai = None  # type: ignore[assignment]


class DraftEnhancerError(Exception):
    """Raised when enhancement fails for any reason (timeout, bad output, API error)."""


class LLMDraftEnhancer:
    """
    Calls an LLM (Anthropic or OpenAI) to produce a personalized outreach draft.

    Instantiate with a provider key and the resume + gap objects that are
    reused across all jobs in a single briefing run.
    """

    _MIN_WORDS = 50
    _MAX_WORDS = 350
    _TIMEOUT_SECONDS = 10

    def __init__(
            self,
            *,
            api_key: str,
            model: Optional[str] = None,
            provider: str = "anthropic",
            resume: ResumeIntelligence,
            gap_by_job_id: Optional[dict[str, GapAnalysis]] = None,
    ) -> None:
        if not api_key:
            raise DraftEnhancerError("LLM API key must not be empty.")
        self._api_key = api_key
        self._model = (model or _config.CAREERCLAW_LLM_MODEL).strip()
        self._provider = provider.strip().lower()
        self._resume = resume
        self._gap_by_job_id = gap_by_job_id or {}

        if self._provider not in ("anthropic", "openai"):
            raise DraftEnhancerError(
                f"Unsupported provider '{self._provider}'. Use 'anthropic' or 'openai'."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enhance(self, *, job: NormalizedJob, gap: GapAnalysis) -> str:
        """
        Return an LLM-enhanced outreach body (no subject line).
        Raises DraftEnhancerError on any failure.
        The API key is never included in the exception message.
        """
        prompt = build_enhance_prompt(job=job, resume=self._resume, gap=gap)
        try:
            if self._provider == "anthropic":
                raw = self._call_anthropic(prompt)
            else:
                raw = self._call_openai(prompt)
        except DraftEnhancerError:
            raise
        except Exception as exc:
            # Sanitize: never let the key propagate through exception messages
            raise DraftEnhancerError(f"LLM call failed: {type(exc).__name__}") from None

        return self._validate(raw)

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    def _call_anthropic(self, prompt: str) -> str:
        if anthropic is None:
            raise DraftEnhancerError(
                "Package 'anthropic' is not installed. Run: pip install anthropic"
            )

        client = anthropic.Anthropic(api_key=self._api_key)
        try:
            message = client.messages.create(
                model=self._model,
                max_tokens=400,
                timeout=self._TIMEOUT_SECONDS,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APITimeoutError:
            raise DraftEnhancerError("Anthropic API timed out after 10 seconds.")
        except anthropic.APIError as exc:
            raise DraftEnhancerError(f"Anthropic API error: {type(exc).__name__}") from None

        # Extract text from response
        for block in message.content:
            if block.type == "text":
                return block.text
        raise DraftEnhancerError("Anthropic returned no text content.")

    def _call_openai(self, prompt: str) -> str:
        if openai is None:
            raise DraftEnhancerError(
                "Package 'openai' is not installed. Run: pip install openai"
            )

        client = openai.OpenAI(api_key=self._api_key, timeout=self._TIMEOUT_SECONDS)
        try:
            response = client.chat.completions.create(
                model=self._model,
                max_tokens=400,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
            )
        except openai.APITimeoutError:
            raise DraftEnhancerError("OpenAI API timed out after 10 seconds.")
        except openai.APIError as exc:
            raise DraftEnhancerError(f"OpenAI API error: {type(exc).__name__}") from None

        content = response.choices[0].message.content
        if not content:
            raise DraftEnhancerError("OpenAI returned empty content.")
        return content

    # ------------------------------------------------------------------
    # Output validation
    # ------------------------------------------------------------------

    def _validate(self, text: str) -> str:
        text = text.strip()
        if not text:
            raise DraftEnhancerError("LLM returned an empty response.")
        word_count = len(text.split())
        if word_count < self._MIN_WORDS:
            raise DraftEnhancerError(
                f"LLM output too short: {word_count} words (minimum {self._MIN_WORDS})."
            )
        if word_count > self._MAX_WORDS:
            raise DraftEnhancerError(
                f"LLM output too long: {word_count} words (maximum {self._MAX_WORDS})."
            )
        return text

def _is_transient_error(err: Exception) -> bool:
    msg = (str(err) or "").lower()
    return any(h in msg for h in TRANSIENT_HINTS)


def _sleep_backoff(attempt: int) -> None:
    # attempt=0 -> ~0.8s, attempt=1 -> ~1.6s, with jitter
    base = 0.8 * (2 ** attempt)
    jitter = random.uniform(0.0, 0.25)
    time.sleep(base + jitter)


@dataclass
class FailoverState:
    consecutive_failures: int = 0
    disabled: bool = False
    disabled_reason: Optional[str] = None
    # Optional: stick to the first successful candidate within a run
    sticky_provider: Optional[str] = None
    sticky_model: Optional[str] = None


class FailoverDraftEnhancer:
    """
    Production-grade wrapper:
    - tries a provider/model chain
    - retries transient errors (rate limit/overloaded/timeout)
    - circuit breaker after N consecutive failures per run
    - optional sticky success (don’t flap once one works)
    """

    def __init__(
            self,
            *,
            api_key_resolver: Callable[[str], Optional[str]],
            candidates: list[tuple[str, str]],
            resume: ResumeIntelligence,
            max_retries: int = 2,
            breaker_consecutive_fails: int = 2,
    ) -> None:
        self._api_key_resolver = api_key_resolver
        self._candidates = candidates
        self._resume = resume
        self._max_retries = max(0, max_retries)
        self._breaker_fails = max(1, breaker_consecutive_fails)
        self._state = FailoverState()
        self._warned_once = False

    def is_disabled(self) -> bool:
        return self._state.disabled

    def _disable(self, reason: str) -> None:
        self._state.disabled = True
        self._state.disabled_reason = reason

    def enhance(self, *, job: NormalizedJob, gap: GapAnalysis) -> str:
        """
        Same signature expectation as LLMDraftEnhancer.enhance(...)
        Pass-through *args/**kwargs to the underlying enhancer.
        """
        if self._state.disabled:
            raise RuntimeError(f"LLM enhancement disabled: {self._state.disabled_reason}")

        # If we already had a successful candidate, try it first (sticky)
        ordered = self._ordered_candidates()

        last_err: Optional[Exception] = None

        for provider, model in ordered:
            api_key = self._api_key_resolver(provider)
            if not api_key:
                last_err = RuntimeError(f"Missing API key for provider: {provider}")
                continue

            enhancer = LLMDraftEnhancer(
                api_key=api_key,
                provider=provider,
                resume=self._resume,
                model=model,
            )

            # Try with limited retries for transient failures
            for attempt in range(self._max_retries + 1):
                try:
                    out = enhancer.enhance(job=job, gap=gap)

                    # Success: reset failure state and stick
                    self._state.consecutive_failures = 0
                    self._state.sticky_provider = provider
                    self._state.sticky_model = model
                    return out

                except Exception as e:
                    last_err = e

                    transient = _is_transient_error(e)
                    if transient and attempt < self._max_retries:
                        _sleep_backoff(attempt)
                        continue

                    # Failed for this candidate (either non-transient, or retries exhausted)
                    break

            # One candidate fully failed
            self._state.consecutive_failures += 1
            if self._state.consecutive_failures >= self._breaker_fails:
                reason = f"circuit-breaker tripped after {self._state.consecutive_failures} failures"
                self._disable(reason)
                break

        # If we get here, everything failed
        if last_err is None:
            last_err = RuntimeError("LLM enhancement failed: no candidates available")
        raise last_err

    def _ordered_candidates(self) -> list[tuple[str, str]]:
        if self._state.sticky_provider and self._state.sticky_model:
            sticky = (self._state.sticky_provider, self._state.sticky_model)
            rest = [c for c in self._candidates if c != sticky]
            return [sticky] + rest
        return list(self._candidates)
