# CareerClaw

[![CI](https://github.com/orestes-garcia-martinez/careerclaw/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/orestes-garcia-martinez/careerclaw/actions/workflows/ci.yml)

**AI-powered job search automation for OpenClaw.**

CareerClaw turns your AI agent into a structured job search workflow:
fetch listings → rank matches → draft outreach → track applications.

Works for any profession. No job board account is required. All data stays
on your machine.

---

## How It Works

1. **Fetches** job listings from RemoteOK and Hacker News Who's Hiring
2. **Ranks** them against your profile using keyword overlap, experience
   alignment, salary fit, and work-mode preference
3. **Drafts** a tailored outreach email for each top match
4. **Tracks** your application pipeline in a local JSON file

One command. Everything local.

---

## Quickstart

### 1. Install

```bash
git clone https://github.com/orestes-garcia-martinez/careerclaw
cd careerclaw
python -m venv .venv

# Activate (macOS/Linux)
source .venv/bin/activate

# Activate (Windows PowerShell)
.\.venv\Scripts\Activate

# Install with dev dependencies
pip install -e ".[dev]"
```

### 2. Set up via OpenClaw (recommended)

If you are running CareerClaw through OpenClaw/ClawHub, the agent will
guide you through setup automatically. Provide your resume and it will
create your profile, ask two questions (work mode and salary), and run
your first briefing.

### 3. Set up manually

Create the runtime directory and your profile:

```bash
mkdir -p .careerclaw
```

Create `.careerclaw/profile.json`:

```json
{
  "skills": ["python", "react", "sql"],
  "target_roles": ["data analyst", "backend engineer"],
  "experience_years": 5,
  "work_mode": "remote",
  "resume_summary": "Experienced analyst with 5 years delivering data pipelines and dashboards.",
  "location": "Austin, TX",
  "salary_min": 90000
}
```

### 4. Run your first briefing

```bash
# Dry run first — no files written, safe to preview
python -m careerclaw.briefing --dry-run

# With your resume for better match quality (recommended)
python -m careerclaw.briefing --resume-pdf .careerclaw/resume.pdf --dry-run

# Full run when you're happy with the results
python -m careerclaw.briefing --resume-pdf .careerclaw/resume.pdf
```

---

## Sample Output

```
=== CareerClaw Daily Briefing ===
User: local-user
Fetched jobs: 244 | After dedupe: 244
Duration: 29482ms

Top Matches:

1) Senior Engineer (Full-Stack) @ Ezra – LATAM REMOTE ONLY  [hn_who_is_hiring]
   score: 0.775 | fit: 41%
   highlights: senior engineer, python, react
   matches: react, python, aws

2) Senior Software Engineer @ Count – REMOTE (UK/Europe/US East Coast)  [hn_who_is_hiring]
   score: 0.725 | fit: 28%
   highlights: senior, engineer
   matches: typescript, python, react

3) Data Infrastructure Engineer @ Stripe – REMOTE  [remoteok]
   score: 0.710 | fit: 35%
   highlights: python, sql, data pipelines
   matches: python, sql, aws

Drafts:

--- Draft #1 ---
Subject: Interest in Senior Engineer (Full-Stack) at Ezra

Hi Ezra team,

I'm reaching out to express interest in the Senior Engineer (Full-Stack)
role. I have 5 years of experience delivering production systems...
```

---

## Free vs Pro

| Feature                                       | Free | Pro         |
|-----------------------------------------------|------|-------------|
| Job ingestion (RemoteOK + HN)                 | ✅    | ✅           |
| Top 3 matches with score breakdown            | ✅    | ✅           |
| Outreach email draft (deterministic)          | ✅    | ✅           |
| Application tracking (local JSON)             | ✅    | ✅           |
| Manual briefing trigger                       | ✅    | ✅           |
| JSON output for agent integration             | ✅    | ✅           |
| Gap analysis (matched vs missing skills)      | ❌    | ✅           |
| LLM-enhanced outreach (your API key)          | ❌    | ✅           |
| Resume intelligence (section-aware weighting) | ❌    | ✅           |
| Scheduled / automated daily briefings         | ❌    | ✅ (roadmap) |
| Additional job sources                        | ❌    | ✅ (roadmap) |
| CSV / Sheets export                           | ❌    | ✅ (roadmap) |

**Pro tier: $39 one-time (lifetime license).**
Purchase at: https://ogm.gumroad.com/l/careerclaw-pro

---

## Pro: Upgrading

Purchase a license key at the link above. Gumroad delivers the key
by email immediately after payment.

### Activating — Docker / self-hosted users

```bash
docker compose run --rm openclaw-cli \
  config set agents.defaults.sandbox.docker.env.CAREERCLAW_PRO_KEY "YOUR-KEY-HERE"
```

Or add it to your `.env` file:

```
CAREERCLAW_PRO_KEY=YOUR-KEY-HERE
```

The key is activated on first use and cached locally as a SHA-256 hash.
Re-validation happens every 7 days (requires internet access).

### Activating — MyClaw managed users

Tell your OpenClaw agent:
> "Set my CAREERCLAW_PRO_KEY to YOUR-KEY-HERE"

The agent stores the key in your OpenClaw config and activates it on
the next CareerClaw run.

---

## Pro: LLM-Enhanced Drafts

With a valid Pro license, you can also supply your own LLM API key to
receive personalized outreach emails referencing your specific resume
signals and each job's requirements. Falls back to the deterministic
template silently on any failure.

```bash
# Anthropic (default — uses claude-sonnet-4-6)
export CAREERCLAW_PRO_KEY=YOUR-KEY-HERE
export CAREERCLAW_LLM_KEY=sk-ant-...
python -m careerclaw.briefing --resume-pdf .careerclaw/resume.pdf

# OpenAI (uses gpt-4o-mini)
export CAREERCLAW_LLM_KEY=sk-...
export CAREERCLAW_LLM_PROVIDER=openai
python -m careerclaw.briefing --resume-pdf .careerclaw/resume.pdf

# Override the model
export CAREERCLAW_LLM_MODEL=claude-haiku-4-5-20251001
```

```powershell
$env:CAREERCLAW_PRO_KEY = "YOUR-KEY-HERE"
$env:CAREERCLAW_LLM_KEY = "sk-ant-..."
```

Estimated cost per run: ~$0.018 at claude-sonnet-4-6 pricing with your
own key.

---

## All CLI Options

```bash
python -m careerclaw.briefing [OPTIONS]

Options:
  --profile PATH        Path to profile.json (default: .careerclaw/profile.json)
  --resume-text PATH    Plain text resume file (.txt)
  --resume-pdf PATH     PDF resume file (.pdf)
  --top-k INT           Number of top matches to return (default: 3)
  --dry-run             Run without writing tracking or run log
  --json                Print JSON output only (machine-readable)
  --analysis MODE       Gap analysis verbosity: off | summary | full (default: summary)
  --no-enhance          Force deterministic drafts even when LLM key is set
  --user-id STRING      User identifier for run tracking (default: local-user)
```

---

## Application Tracking

Tracking is written automatically on each non-dry-run. Status options:

`saved` → `applied` → `interview` → `rejected`

Runtime files — all stored under `.careerclaw/` (gitignored by default):

| File                        | Contents                                         |
|-----------------------------|--------------------------------------------------|
| `profile.json`              | Your profile                                     |
| `resume.txt` / `resume.pdf` | Your resume                                      |
| `tracking.json`             | Saved jobs keyed by stable `job_id`              |
| `runs.jsonl`                | Append-only run log (one line per run)           |
| `resume_intel.json`         | Cached resume intelligence                       |
| `.license_cache`            | Pro license validation cache (SHA-256 hash only) |

---

## Match Scores Explained

CareerClaw scores each job on four dimensions:

| Dimension            | Weight | What it measures                                             |
|----------------------|--------|--------------------------------------------------------------|
| Keyword overlap      | 50%    | Skills and role terms shared between job and profile         |
| Experience alignment | 20%    | Your years vs job requirements                               |
| Salary alignment     | 15%    | Your minimum vs the posted range (neutral if no salary data) |
| Work-mode match      | 15%    | Remote/onsite/hybrid preference match                        |

**`score`** is the composite (0.0–1.0). **`fit`** is the resume-to-job
overlap percentage from gap analysis — it requires a resume file to be
meaningful. Fit scores of 40%+ are strong; the practical ceiling against
real job postings is ~50% due to company names and location tokens in
the denominator.

---

## HN Thread ID — Monthly Update

The Hacker News "Who is Hiring?" thread is posted on the first weekday
of each month. Update the ID in `careerclaw/config.py` to get fresh
listings:

```python
HN_WHO_IS_HIRING_THREAD_ID = 46857488  # Update monthly
```

Find the current thread: search `site:news.ycombinator.com "who is hiring"`
and copy the numeric ID from the URL.

---

## Architecture

---

## LLM Architecture

CareerClaw uses **two separate LLM layers**:

- **Agent layer (OpenClaw)**: the model that powers your OpenClaw agent (chat, tool use, routing). Configure it via OpenClaw config:
  - `openclaw-cli config set agents.defaults.model.primary openai/gpt-5.2`
  - Requires `OPENAI_API_KEY` and/or `ANTHROPIC_API_KEY` in your environment.

- **Draft layer (CareerClaw Pro enhancement)**: an optional Pro-only step that enhances deterministic outreach drafts using your own provider key(s). It is **independent** from the agent model.
  - Recommended: provider-specific keys `CAREERCLAW_OPENAI_KEY` / `CAREERCLAW_ANTHROPIC_KEY` (supports mixed failover chains)
  - Legacy: `CAREERCLAW_LLM_KEY` (single-key override)
  - Failover chain: `CAREERCLAW_LLM_CHAIN=openai/gpt-5.2,openai/gpt-4o-mini,anthropic/claude-sonnet-4-6`

If enhancement fails (rate limits, auth issues, provider outage), CareerClaw **silently falls back** to deterministic drafts.

```
profile.json + resume file
        │
        ▼
fetch_all_jobs()          ← RemoteOK RSS + HN Firebase API
        │
        ▼
deduplicate()             ← stable job_id hash
        │
        ▼
rank_jobs()               ← keyword + experience + salary + work-mode
        │
        ▼
build_resume_intelligence()   ← section-aware keyword extraction (Pro)
gap_analysis()                ← matched vs missing signals (Pro)
        │
        ▼
draft_outreach()          ← deterministic template (Free)
llm_enhance()             ← LLM email via your API key (Pro)
        │
        ▼
persist_tracking()        ← tracking.json + runs.jsonl
        │
        ▼
output bundle             ← console summary + JSON payload
```

**Module layers** (higher layers may import lower, never the reverse):

1. `careerclaw/core/` — text processing, shared utilities
2. `careerclaw/matching/`, `careerclaw/resume_intel.py` — domain logic
3. `careerclaw/adapters/`, `careerclaw/io/` — I/O and source adapters
4. `careerclaw/tracking.py` — persistence
5. `careerclaw/briefing.py` — pipeline orchestration and CLI entry point

---

## Development

### Running tests

```bash
# All unit and integration tests (offline, no network)
python -m pytest -q

# Live source smoke test (requires network — run before releases)
python scripts/smoke_test_sources.py

# Pro license end-to-end smoke test (requires CAREERCLAW_PRO_KEY + network)
CAREERCLAW_PRO_KEY=<your-key> python scripts/smoke_test_license.py
```

### Project structure

```
careerclaw/
├── adapters/          # RemoteOK RSS + HN Firebase adapters
├── core/              # Shared text processing
├── io/                # Resume loaders (txt + PDF)
├── llm/               # LLM draft enhancer (Pro)
├── matching/          # Scoring engine
├── briefing.py        # Pipeline orchestrator + CLI entry point
├── config.py          # Environment and source configuration
├── drafting.py        # Deterministic draft templates
├── gap.py             # Gap analysis engine
├── license.py         # Pro license activation and validation
├── models.py          # Canonical data schemas
├── requirements.py    # Job requirements extraction
├── resume_intel.py    # Resume intelligence
├── sources.py         # Source aggregation
└── tracking.py        # Tracking repository
docs/
├── architecture.md
└── data-schema.md
scripts/
├── smoke_test_sources.py   # Live source fetch test
└── smoke_test_license.py   # Pro license end-to-end test
tests/
├── contract/          # Adapter contract tests (offline fixtures)
├── fixtures/          # Test data
└── unit/              # Unit and integration tests
```

---

## Security & Privacy

CareerClaw is built on a local-first architecture. Your data never
leaves your machine unless you configure an LLM key.

- **No backend.** No telemetry. No analytics endpoint.
- **API keys never stored.** `CAREERCLAW_LLM_KEY` is read from the
  environment at runtime and never written to disk or logs.
- **License cache is hash-only.** `CAREERCLAW_PRO_KEY` is validated
  against Gumroad on first use. Only a SHA-256 hash of the key is
  written to `.careerclaw/.license_cache` — the raw key is never stored.
- **No PII transmission.** Your resume, profile, and application history
  are stored only in `.careerclaw/` on your local machine.
- **External calls:** `remoteok.com` (RSS, no auth),
  `hacker-news.firebaseio.com` (public API, no auth), and
  `api.gumroad.com` (license validation only) only.
- **LLM calls** go directly to your configured provider (Anthropic or
  OpenAI) using your own key — no CareerClaw server in the middle.
- **VirusTotal clean** on every release.

See [SECURITY.md](SECURITY.md) for the vulnerability disclosure policy.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

---

## License

- **Free tier:** MIT License — see [LICENSE](LICENSE)
- **Pro tier:** Commercial license

---

## Support

- **GitHub Issues:** for bug reports and feature requests
- **Response SLA:** critical bugs < 48h · general questions < 72h
- **Security disclosures:** see [SECURITY.md](SECURITY.md)
- **Pro inquiries:** orestes.garcia.martinez@gmail.com