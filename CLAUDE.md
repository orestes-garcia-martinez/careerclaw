# CLAUDE.md — AI Assistant Guide for CareerClaw

This file provides context for AI assistants (Claude and others) working in
this repository. Read it before making any changes.

---

## What This Project Is

CareerClaw is a **local-first, CLI-based job search assistant** written in
Python. It fetches job listings from public sources (RemoteOK, Hacker News
"Who's Hiring" threads), scores them against a user's resume and profile,
generates outreach email drafts, and tracks applications — all without a
backend server or telemetry.

It is designed to work as a standalone CLI tool and as an **OpenClaw agent
skill** (see `SKILL.md`). There is no web frontend, no database, and no
hosted API.

**Current version**: 0.7.0
**Python requirement**: ≥ 3.11 (CI tests 3.12 and 3.13)

---

## Repository Layout

```
careerclaw/                  # Main Python package
├── adapters/                # Job source adapters
│   ├── remoteok.py          # RemoteOK RSS fetcher
│   └── hn.py                # Hacker News Firebase API fetcher
├── core/
│   └── text_processing.py   # Shared tokenization, phrase extraction, stopwords
├── io/
│   └── resume_loader.py     # PDF (via pypdf) and plain-text resume loaders
├── llm/
│   └── enhancer.py          # LLM draft enhancement with failover chain (Pro)
├── matching/                # Scoring and ranking engine
├── briefing.py              # Pipeline orchestrator + CLI entry point
├── config.py                # All environment variables and constants
├── drafting.py              # Deterministic email draft generation
├── gap.py                   # Gap analysis (matched vs missing skills) [Pro]
├── license.py               # Pro license validation and caching
├── models.py                # Canonical dataclass schemas (NormalizedJob, etc.)
├── requirements.py          # Job requirements extraction from text
├── resume_intel.py          # Resume intelligence extraction [Pro]
├── sources.py               # Source aggregation with per-source error handling
└── tracking.py              # JSON-based application tracking persistence

tests/
├── conftest.py              # Shared pytest fixtures (load_json, load_text)
├── fixtures/                # Offline test data (JSON, text)
├── contract/
│   └── test_adapters.py     # Offline adapter contract tests
└── unit/                    # Unit and integration tests

scripts/
├── smoke_test_sources.py    # Live network smoke test (run manually)
└── smoke_test_license.py    # Pro license end-to-end validation

docs/                        # Documentation stubs
docker/                      # Docker configuration
.github/workflows/ci.yml     # GitHub Actions CI
```

---

## Architecture and Data Flow

```
User Profile (JSON) + Resume (PDF or TXT)
        ↓
fetch_all_jobs()           sources.py
  ├─ RemoteOK RSS          adapters/remoteok.py
  └─ HN Firebase API       adapters/hn.py
        ↓
deduplicate_jobs()         stable job_id = SHA-256 hash of url
        ↓
extract_job_requirements() requirements.py
        ↓
build_resume_intelligence() resume_intel.py  [Pro]
  ├─ Tokenize resume
  ├─ Extract phrases
  └─ Apply section weighting
        ↓
rank_jobs()                matching/
  ├─ Keyword overlap  50%
  ├─ Experience align 20%
  ├─ Salary align     15%
  └─ Location align   15%
        ↓
analyze_gap()              gap.py  [Pro]
        ↓
draft_outreach()           drafting.py  (deterministic)
        ↓
llm_enhance()              llm/enhancer.py  [Pro + LLM key, silent fallback]
        ↓
persist_tracking()         tracking.py
  ├─ .careerclaw/tracking.json   (upsert by job_id)
  └─ .careerclaw/runs.jsonl      (append-only run log)
        ↓
JSON + console output
```

### Key design principles

- **Graceful degradation**: every external call (adapters, LLM, license check)
  is wrapped in `try/except`. A single failure never breaks the full pipeline.
- **Deterministic free tier**: no AI in the free path. The LLM enhancer is
  always optional and falls back silently to the deterministic draft.
- **Local-first**: no data leaves the machine except for user-initiated API
  calls to LLM providers and the Pro license validation endpoint.
- **No telemetry**: no tracking, analytics, or logging to any external service.

---

## Module Layering Rules

Imports must flow **downward only**. Higher layers may import lower layers,
but never the reverse.

```
Layer 1 (lowest):  careerclaw/core/         — text utilities, shared helpers
Layer 2:           careerclaw/matching/
                   careerclaw/resume_intel.py
Layer 3:           careerclaw/adapters/
                   careerclaw/io/
Layer 4:           careerclaw/tracking.py
                   careerclaw/gap.py
                   careerclaw/drafting.py
                   careerclaw/llm/
Layer 5 (highest): careerclaw/briefing.py   — nothing imports this module
```

If a change requires importing `briefing.py` from a lower layer, the design
needs rethinking. Do not introduce circular imports.

---

## Data Models (`careerclaw/models.py`)

All inter-module data passes through canonical dataclasses defined in
`models.py`. No adapter-specific fields should leak past the adapter boundary.

Key types:
- `NormalizedJob` — a job listing normalized from any source
- `ResumeIntelligence` — extracted signals from the user's resume
- `JobRequirements` — extracted requirements from a job listing
- `GapAnalysis` — matched and missing skills for a job
- `ApplicationStatus` (Enum) — `SEEN`, `APPLIED`, `INTERVIEWING`, `OFFERED`, `REJECTED`
- `JobSource` (Enum) — `REMOTEOK`, `HN`

---

## Configuration (`careerclaw/config.py`)

All configuration lives here. Do not hardcode URLs, thresholds, or API
endpoints in other modules — add a constant to `config.py` instead.

### Environment variables

| Variable | Purpose | Required |
|---|---|---|
| `CAREERCLAW_PRO_KEY` | One-time Pro license key (Polar.sh) | No (free tier) |
| `CAREERCLAW_ANTHROPIC_KEY` | Anthropic key for LLM draft enhancement | No |
| `CAREERCLAW_OPENAI_KEY` | OpenAI key for LLM draft enhancement | No |
| `CAREERCLAW_LLM_KEY` | Legacy single-provider key override | No |
| `CAREERCLAW_LLM_PROVIDER` | `"anthropic"` (default) or `"openai"` | No |
| `CAREERCLAW_LLM_MODEL` | Override default model name | No |
| `CAREERCLAW_LLM_CHAIN` | Failover chain, e.g. `openai/gpt-5.2,anthropic/claude-sonnet-4-6` | No |
| `CAREERCLAW_LLM_MAX_RETRIES` | Retry count per provider (default: 2) | No |
| `CAREERCLAW_LLM_CIRCUIT_BREAKER_FAILS` | Circuit breaker threshold (default: 2) | No |
| `OPENCLAW_GATEWAY_TOKEN` | Agent gateway auth (OpenClaw integration only) | No |

### Local runtime directory (`.careerclaw/` — gitignored)

| File | Contents |
|---|---|
| `profile.json` | User profile (skills, experience, salary, location prefs) |
| `resume.txt` / `resume.pdf` | User's resume |
| `tracking.json` | Application tracking (job_id → status) |
| `runs.jsonl` | Append-only run log |
| `resume_intel.json` | Cached resume intelligence |
| `.license_cache` | SHA-256 hash of Pro key (never the raw key) |

**Never commit anything from `.careerclaw/`.**

---

## Development Setup

```bash
git clone https://github.com/orestes-garcia-martinez/careerclaw
cd careerclaw
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .\.venv\Scripts\Activate       # Windows PowerShell
pip install -e ".[dev]"
python -m pytest -q              # All tests must pass before any changes
```

---

## Testing

All tests run **offline**. No network access is required or permitted in unit
or contract test suites. CI explicitly unsets `CAREERCLAW_LLM_KEY` to enforce
that LLM tests use mocked responses.

```bash
# Run the full offline suite
python -m pytest -q

# Run a specific test file
python -m pytest tests/unit/test_matching_engine.py -q

# Run tests matching a keyword
python -m pytest -q -k "salary"

# Live network smoke test — run manually before releases only
python -m scripts.smoke_test_sources
```

### Test requirements by change type

| Change | Required test |
|---|---|
| New scoring logic | Unit test in `tests/unit/` |
| New or modified adapter | Contract test in `tests/contract/` with offline fixture |
| New pipeline behavior | Integration test in `test_briefing_orchestration.py` |
| New stopword | Unit test verifying the term is filtered |
| Bug fix | Regression test that would have caught the original bug |

### Writing tests

- Use `load_json` and `load_text` fixtures from `conftest.py` — do not read
  fixture files inline.
- Mock network calls with `monkeypatch` in contract tests.
- Use `assert_normalized_job_contract()` in adapter contract tests to validate
  all `NormalizedJob` invariants in one call.
- **Never write a test that requires a real `CAREERCLAW_LLM_KEY`.**

---

## CLI Entry Point

```bash
python -m careerclaw.briefing [options]
```

| Flag | Default | Description |
|---|---|---|
| `--profile PATH` | `.careerclaw/profile.json` | User profile |
| `--resume-text PATH` | — | Plain-text resume |
| `--resume-pdf PATH` | — | PDF resume |
| `--top-k INT` | `3` | Number of top matches to return |
| `--dry-run` | `false` | Skip all file writes |
| `--json` | `false` | JSON-only output (no console summary) |
| `--analysis MODE` | `off` | Gap analysis verbosity: `off`, `summary`, `full` |
| `--no-enhance` | `false` | Force deterministic draft (skip LLM) |
| `--user-id STRING` | — | User identifier for tracking |

---

## Code Style Conventions

- `from __future__ import annotations` at the top of **every** module.
- Explicit, readable code over clever abstractions. Prefer clarity.
- Docstrings on all public functions. One-liners are fine for simple helpers.
- No linter or formatter is enforced — match the surrounding code style.
- Snake case for functions and variables, PascalCase for classes and enums,
  `ALL_CAPS` for module-level constants.
- Prefix `_` for private/internal functions not part of a module's public API.
- Dataclasses with `frozen=True` for immutable domain objects.
- Protocols (structural subtyping) for injectable dependencies
  (e.g., `DraftEnhancer`, `TrackingRepository`).

---

## Branch Workflow

| Branch | Purpose |
|---|---|
| `main` | Stable tagged releases only. **Never commit directly.** |
| `dev` | Active development. All PRs target this branch. |
| `feature/<name>` | Your working branch, created from `dev`. |

PRs targeting `main` directly will be closed.

```bash
git checkout dev
git pull origin dev
git checkout -b feature/your-change-name
# ... make changes, commit, push ...
# Open PR targeting dev
```

---

## Commit Message Style

Use short, imperative sentences that describe the change:

```
Fix salary scoring when job_max is None
Add stopwords: apply, candidate, competitive
Extend ResumeIntelligence to accept target_roles
```

One logical change per commit. Do not use vague messages like `fix bug`,
`update`, or `changes`.

---

## Adding a New Job Source Adapter

1. Add `careerclaw/adapters/your_source.py` implementing `fetch_jobs() -> list[NormalizedJob]`.
2. Normalize all output to `NormalizedJob` — no source-specific fields past the adapter boundary.
3. Register the adapter in `careerclaw/sources.py` inside a `try/except` block.
4. Add any config constants (URLs, defaults) to `careerclaw/config.py`.
5. Add a real offline fixture to `tests/fixtures/`.
6. Add contract tests in `tests/contract/test_adapters.py`.
7. Update the smoke test script.
8. Only use publicly accessible sources that permit automated access per their ToS.

---

## What Must Not Be Done

- Do not introduce external dependencies without prior discussion.
- Do not store or log API keys in any form.
- Do not add a backend server, telemetry endpoint, or persistent remote state.
- Do not scrape authenticated or restricted platforms (LinkedIn, Indeed, etc.).
- Do not break the offline test suite.
- Do not expand agent permissions beyond what is documented in `SKILL.md`.
- Do not commit anything in `.careerclaw/` (tracked by `.gitignore`).
- Do not write tests that require a live LLM API key.
- Do not import `careerclaw.briefing` from any lower-layer module.

---

## Pro vs Free Tier

| Feature | Free | Pro |
|---|---|---|
| Job fetching and deduplication | Yes | Yes |
| Four-dimension scoring and ranking | Yes | Yes |
| Deterministic email draft | Yes | Yes |
| Application tracking | Yes | Yes |
| Resume intelligence extraction | No | Yes |
| Gap analysis | No | Yes |
| LLM-enhanced drafts | No | Yes |

Pro features are gated on `CAREERCLAW_PRO_KEY`. License validation uses
LemonSqueezy/Polar.sh. Only a SHA-256 hash of the key is cached locally; the
raw key is never persisted. A 7-day revalidation window applies, with a 24-hour
grace period on network failure.

---

## Security Notes

- No secrets are ever written to disk (only key hashes in `.license_cache`).
- File permissions on Unix: `tracking.json` is chmod 600 where possible.
- The LLM call chain (provider failover, circuit breaker) is in
  `careerclaw/llm/enhancer.py`. All errors are caught and fall back to the
  deterministic draft without surfacing API credentials.
- See `SECURITY.md` for the vulnerability disclosure policy.
