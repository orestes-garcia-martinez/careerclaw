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
from typing import Optional

from careerclaw.gap import GapAnalysis
from careerclaw.llm.prompt import _SYSTEM_PROMPT, build_enhance_prompt
from careerclaw.models import NormalizedJob, UserProfile
from careerclaw.resume_intel import ResumeIntelligence
from careerclaw import config as _config

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
            provider: str = "anthropic",
            resume: ResumeIntelligence,
            gap_by_job_id: Optional[dict[str, GapAnalysis]] = None,
    ) -> None:
        if not api_key:
            raise DraftEnhancerError("LLM API key must not be empty.")
        self._api_key = api_key
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
                model=_config.CAREERCLAW_LLM_MODEL,
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
                model=_config.CAREERCLAW_LLM_MODEL,
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
