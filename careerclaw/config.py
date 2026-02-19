# careerclaw/config.py

import os

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

# --- User-Agent (update when repo is public) ---

USER_AGENT = "CareerClaw/0.1 (+https://github.com/orestes-garcia-martinez/careerclaw)"

# --- LLM Draft Enhancement (Pro Tier) ---

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
    """Return True only when a non-empty LLM key is present in the environment."""
    return bool(CAREERCLAW_LLM_KEY)
