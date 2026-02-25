# careerclaw/config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Tuple

# --- Sources (MVP Locked) ---

REMOTEOK_RSS_URL = "https://remoteok.com/remote-dev-jobs.rss"

# Update monthly (manual in MVP)
# Google: site:news.ycombinator.com Who is hiring February 2026
HN_WHO_IS_HIRING_THREAD_ID = 46857488

# --- Guardrails (MVP) ---

REMOTEOK_MAX_ITEMS = 50
HN_MAX_COMMENTS = 200

# --- Networking ---

HTTP_TIMEOUT_SECONDS = 20

# --- User-Agent ---

USER_AGENT = "CareerClaw/0.5 (+https://github.com/orestes-garcia-martinez/careerclaw)"

# --- CareerClaw Pro License ---

# One-time license key purchased at https://orestes-garcia-martinez.lemonsqueezy.com
# Gates: gap analysis, resume intelligence, LLM-enhanced drafts.
# Never logged, never written to disk (only a hash is cached locally).
CAREERCLAW_PRO_KEY: str | None = os.environ.get("CAREERCLAW_PRO_KEY") or None

def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default

def _parse_llm_chain(raw: str | None) -> List[Tuple[str, str]]:
    """
    Parses: "openai/gpt-5.2,openai/gpt-4o-mini,anthropic/claude-sonnet-4-6"
    -> [("openai","gpt-5.2"), ...]
    """
    if not raw:
        return []
    items: List[Tuple[str, str]] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "/" not in part:
            # Allow "gpt-5.2" shorthand -> assume openai
            items.append(("openai", part))
            continue
        provider, model = part.split("/", 1)
        provider = provider.strip().lower()
        model = model.strip()
        if provider and model:
            items.append((provider, model))
    return items

@dataclass(frozen=True)
class LLMFailoverConfig:
    chain: List[Tuple[str, str]]
    max_retries: int
    breaker_consecutive_fails: int


def load_llm_failover_config() -> LLMFailoverConfig:
    chain_raw = os.getenv(
        "CAREERCLAW_LLM_CHAIN",
        "openai/gpt-5.2,openai/gpt-4o-mini,anthropic/claude-sonnet-4-6",
    )
    return LLMFailoverConfig(
        chain=_parse_llm_chain(chain_raw),
        max_retries=_env_int("CAREERCLAW_LLM_MAX_RETRIES", 2),
        breaker_consecutive_fails=_env_int("CAREERCLAW_LLM_CIRCUIT_BREAKER_FAILS", 2),
    )

def pro_licensed() -> bool:
    """Return True when a valid Pro license key is present and verified."""
    from careerclaw.license import pro_licensed as _check
    return _check(CAREERCLAW_PRO_KEY)


# --- LLM Draft Enhancement (Pro Tier — also requires pro_licensed()) ---

# User-provided API key for LLM draft enhancement.
# Never logged, never written to disk, never included in structured output.
CAREERCLAW_LLM_KEY: str | None = os.environ.get("CAREERCLAW_LLM_KEY") or None

# Provider selection: "anthropic" | "openai"  (default: anthropic)
CAREERCLAW_LLM_PROVIDER: str = os.environ.get("CAREERCLAW_LLM_PROVIDER", "anthropic").strip().lower()

# Model selection per provider.
# Anthropic default: claude-sonnet-4-6 (strong quality, affordable at user's own key)
# OpenAI default:    gpt-4o-mini
# Override via CAREERCLAW_LLM_MODEL env var.
_DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o-mini",
}
CAREERCLAW_LLM_MODEL: str = (
        os.environ.get("CAREERCLAW_LLM_MODEL", "").strip()
        or _DEFAULT_MODELS.get(CAREERCLAW_LLM_PROVIDER, "claude-sonnet-4-6")
)


def llm_configured() -> bool:
    return bool(
        os.getenv("CAREERCLAW_OPENAI_KEY")
        or os.getenv("CAREERCLAW_ANTHROPIC_KEY")
        or os.getenv("CAREERCLAW_LLM_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
    )
