# CareerClaw

[![CI](https://github.com/orestes-garcia-martinez/careerclaw/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/orestes-garcia-martinez/careerclaw/actions/workflows/ci.yml)

**Privacy-first job search automation for OpenClaw.**

CareerClaw turns your AI agent into a structured daily workflow:
fetch listings → rank matches → draft outreach → track applications.

- **Local-first:** your resume and results stay on your machine
- **No subscription:** one-time purchase for Pro
- **Bring your own LLM API key (optional):** use OpenAI/Anthropic to enhance drafts

Works best for roles where job boards and public listings are common (engineering, product, design, ops, marketing, finance).

---

## How It Works

1. **Fetches** job listings from supported sources (baseline sources are always available; integrations expand over time)
2. **Ranks** them against your profile using keyword overlap, experience alignment, salary fit, and work-mode preference
3. **Drafts** outreach for each top match (deterministic template in Free; optional LLM enhancement in Pro)
4. **Tracks** your application pipeline locally (JSON files under `.careerclaw/`)

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

If you are running CareerClaw through OpenClaw/ClawHub, the agent can guide you through setup. Provide your resume and it will create your profile, ask a couple of preference questions (work mode + salary), and run your first briefing.

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
...
```

---

## Free vs Pro

| Feature                                       | Free | Pro              |
|-----------------------------------------------|------|------------------|
| Job ingestion (baseline supported sources)    | ✅    | ✅               |
| Additional job sources / integrations         | ❌    | ✅ (as released) |
| Top matches with score breakdown              | ✅    | ✅               |
| Outreach email draft (deterministic)          | ✅    | ✅               |
| Application tracking (local JSON)             | ✅    | ✅               |
| Manual briefing trigger                       | ✅    | ✅               |
| JSON output for agent integration             | ✅    | ✅               |
| Gap analysis (ATS shadowing)                  | ❌    | ✅               |
| LLM-enhanced outreach (your LLM API key)      | ❌    | ✅               |
| Resume intelligence (section-aware weighting) | ❌    | ✅               |
| Scheduled / automated daily briefings         | ❌    | ✅ (roadmap)     |
| CSV / Sheets export                           | ❌    | ✅ (roadmap)     |

**Pro tier: $39 one-time (lifetime license).**

Purchase on Gumroad:
https://ogm.gumroad.com/l/careerclaw-pro

---

## Optional: Pro + Setup & Configuration (1:1)

If you want it running quickly, Gumroad also offers **“Pro + Setup & Configuration (1:1)”** (limited slots). It includes:

- Install CareerClaw into your OpenClaw workspace
- Configure env vars + optional LLM API keys
- Get your first daily briefing running successfully
- Async troubleshooting included

(Select that version at checkout.)

---

## Pro: Upgrading

Purchase a license key on Gumroad. Gumroad delivers the key by email immediately after payment.

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

The agent stores the key in your OpenClaw config and activates it on the next CareerClaw run.

---

## Pro: LLM-Enhanced Drafts

With a valid Pro license, you can supply your own LLM API key to receive personalized outreach emails. CareerClaw falls back to the deterministic template silently on any failure.

```bash
export CAREERCLAW_PRO_KEY=YOUR-KEY-HERE
export CAREERCLAW_LLM_KEY=sk-...
python -m careerclaw.briefing --resume-pdf .careerclaw/resume.pdf
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
| `resume_intel.json`         | Cached resume intelligence (Pro)                 |
| `.license_cache`            | Pro license validation cache (SHA-256 hash only) |

---

## Security & Privacy

CareerClaw is built on a local-first architecture. Your data never leaves your machine unless you configure an LLM API key.

- **No backend.** No telemetry. No analytics endpoint.
- **API keys never stored.** LLM keys are read from the environment at runtime and never written to disk or logs.
- **License cache is hash-only.** Only a SHA-256 hash of the license key is written locally — the raw key is never stored.
- **No PII transmission.** Your resume, profile, and application history are stored only in `.careerclaw/` on your local machine.

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
