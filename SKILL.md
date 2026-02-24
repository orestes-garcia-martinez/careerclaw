---
name: careerclaw
version: 0.5.0
description: >
  Run a job search briefing, find job matches, draft outreach emails,
  or track job applications. Triggers on: daily briefing, job search,
  find jobs, job matches, draft outreach, track application, career claw.
metadata:
  openclaw:
    emoji: "🦞"
    primaryEnv: CAREERCLAW_PRO_KEY
    requires:
      bins: ["python3"]
    optionalEnv:
      - name: CAREERCLAW_PRO_KEY
        description: "CareerClaw Pro license key. Purchase at https://orestes-garcia-martinez.lemonsqueezy.com/buy/careerclaw-pro — unlocks gap analysis, resume intelligence, and LLM-enhanced drafts."
      - name: CAREERCLAW_LLM_KEY
        description: "API key for LLM-enhanced outreach drafts (Pro only). Anthropic or OpenAI."
      - name: CAREERCLAW_LLM_PROVIDER
        description: "'anthropic' (default) or 'openai'"
      - name: CAREERCLAW_LLM_MODEL
        description: "Override the default model. Defaults: claude-sonnet-4-6 / gpt-4o-mini"
---

# CareerClaw

Fetch job listings from RemoteOK and Hacker News Who's Hiring, rank them
against the user's profile, generate tailored outreach email drafts, and
persist an application tracking log — all locally, with no backend.

---

## First Run: Setup

### Step 1 — Install

```bash
pip install -e .
mkdir -p .careerclaw
```

### Step 2 — Create the user profile from their resume

Ask the user to provide their resume (PDF or plain text file). Do not
ask them to fill in a JSON form.

Read the resume and extract the following fields:

| Field              | Type                                 | How to extract                                   |
|--------------------|--------------------------------------|--------------------------------------------------|
| `skills`           | list of strings                      | Skills section + tech mentions throughout        |
| `target_roles`     | list of strings                      | Current/recent title + inferred career direction |
| `experience_years` | integer                              | Calculate from earliest to most recent role      |
| `resume_summary`   | string (1–3 sentences)               | Summary section, or synthesize from experience   |
| `location`         | string or null                       | Contact header                                   |
| `salary_min`       | integer (annual USD) or null         | Cannot be extracted — ask the user (optional)    |
| `work_mode`        | `"remote"` / `"onsite"` / `"hybrid"` | Cannot be extracted — ask the user               |

Only ask the user two questions:
1. What is your preferred work mode — remote, onsite, or hybrid?
2. Do you have a minimum salary in mind? (optional — they can skip)

Once you have all values, write `.careerclaw/profile.json`:

```json
{
  "skills": ["python", "react", "sql"],
  "target_roles": ["data analyst", "backend engineer"],
  "experience_years": 5,
  "work_mode": "remote",
  "resume_summary": "Experienced analyst with 5 years delivering data pipelines...",
  "location": "Austin, TX",
  "salary_min": 90000
}
```

Save the resume file to `.careerclaw/resume.txt` (or `.careerclaw/resume.pdf`)
so it can be passed on every subsequent run for better match quality.

Confirm the profile with the user before proceeding, showing the
extracted values. Offer to correct any field they disagree with.

### Step 3 — Run the first briefing

Once the profile is confirmed, immediately run:

```bash
python -m careerclaw.briefing --resume-text .careerclaw/resume.txt --dry-run
```

(Use `--resume-pdf` if the resume was provided as a PDF.)

Use `--dry-run` for the first run so nothing is written until the user
confirms they are happy with the results.

---

## Running the Daily Briefing

```bash
# Standard run (writes tracking.json and runs.jsonl)
python -m careerclaw.briefing --resume-text .careerclaw/resume.txt

# Dry run — no files written, safe for previewing
python -m careerclaw.briefing --resume-text .careerclaw/resume.txt --dry-run

# JSON-only output (for agent parsing)
python -m careerclaw.briefing --resume-text .careerclaw/resume.txt --json

# Control analysis verbosity
python -m careerclaw.briefing --analysis off      # minimal
python -m careerclaw.briefing --analysis summary  # fit % and highlights (default)
python -m careerclaw.briefing --analysis full     # gap keywords and phrases

# Return more than 3 results
python -m careerclaw.briefing --top-k 5
```

**Always pass `--resume-text` or `--resume-pdf` on every run** to ensure
resume intelligence is active. Without it, fit scores will be low (1–5%)
though match scores remain valid.

**Use `--dry-run` when the user just wants to see matches** without
updating their tracking log.

---

## Interpreting the Output

**Console summary fields:**

- `score` — composite match score (0.0–1.0). Higher is better.
- `fit` — resume-to-job overlap percentage.
- `matches` — skills/keywords found in both the job and the user's profile.
- `highlights` — top resume signals relevant to this role (summary mode).

**JSON top-level fields:**

- `fetched_jobs` — total jobs retrieved before deduplication
- `top_matches` — ranked list with scores, explanation, and gap analysis
- `drafts` — outreach email drafts per job (`channel: "email"`)
- `tracking` — new entries created vs already-present
- `duration_ms` — pipeline runtime
- `resume_intelligence` — extracted keywords and phrase signals

**Draft format:** Each draft contains a `Subject:` line followed by the
email body. Present both to the user.

---

## Presenting Results to the User

Follow these rules every time you present briefing results in a chat
interface (Telegram, Discord, etc.).

### Matches

For each match, always show:
- Job title and company
- Location and work mode
- Score (and fit % if available)
- 1–2 matched skills or keywords
- Any relevant warning (e.g. entry-level listing, location mismatch,
  LATAM-only, contract vs full-time)

### Drafts

The `drafts` field in the JSON output contains full outreach **email
drafts** — not summaries. Each draft has a `Subject:` line and a
complete email body ready to send.

**Always follow these rules when presenting drafts:**

1. Make it explicit that these are **email drafts** — do not let the
   user assume they are just summaries or notes.
2. In a chat interface, show a one-sentence summary of each draft's
   angle to keep the briefing readable (e.g. "Leads with your React +
   TypeScript stack and positions your AI experience as a differentiator").
3. Always close the results with this offer:

   > "Each match has a full outreach email draft ready — subject line
   > and complete body. Want me to show the full email for any of these?"

4. When the user asks for a full draft, output the complete `Subject:`
   line and email body verbatim from the JSON. Do not paraphrase or
   shorten it.
5. If `"enhanced": true` on a draft, tell the user it is
   **LLM-enhanced** and personalized from their resume signals.
   If `"enhanced": false`, tell the user it is a **template draft**
   and offer to upgrade via `CAREERCLAW_LLM_KEY` if not already set.

### After the briefing

Always end with a clear next-step prompt, for example:

> "Want the full email for any of these? I can also update a job's
> tracking status, bump to more results with `--top-k 5`, or run a
> dry-run if you just want to preview without saving."

### Dry-run vs real run

Always tell the user which mode was used:
- Dry run: "This was a **dry run** — nothing was saved to your tracking log."
- Real run: "**N jobs saved** to your tracking log."

---

## Upgrading to Pro

CareerClaw Pro unlocks gap analysis, resume intelligence, and LLM-enhanced
outreach drafts. It requires a one-time license key.

**Purchase:** https://orestes-garcia-martinez.lemonsqueezy.com/buy/careerclaw-pro
**Price:** $39 (lifetime, one-time payment)

After purchase, LemonSqueezy emails the license key immediately.

### Activating Pro — Docker / self-hosted users

```bash
docker compose run --rm openclaw-cli \
  config set agents.defaults.sandbox.docker.env.CAREERCLAW_PRO_KEY "YOUR-KEY-HERE"
```

Or add it to your `.env` file:
```
CAREERCLAW_PRO_KEY=YOUR-KEY-HERE
```

The key is activated automatically on first use and cached locally.
Re-validation happens every 7 days (requires internet access).

### Activating Pro — MyClaw managed users

Tell your OpenClaw agent:
> "Set my CAREERCLAW_PRO_KEY to YOUR-KEY-HERE"

The agent will store the key in your OpenClaw config and activate it
on the next CareerClaw run.

---

## LLM-Enhanced Drafts (Pro — user's own API key)

When `CAREERCLAW_PRO_KEY` is set and valid, and `CAREERCLAW_LLM_KEY`
is also provided, each top match receives an LLM-enhanced outreach email
referencing the user's specific resume signals and the job's requirements.
Falls back to the deterministic template silently on any failure.

```bash
# Anthropic (default provider, uses claude-sonnet-4-6)
export CAREERCLAW_LLM_KEY=sk-ant-...
python -m careerclaw.briefing --resume-text .careerclaw/resume.txt

# OpenAI (uses gpt-4o-mini)
export CAREERCLAW_LLM_KEY=sk-...
export CAREERCLAW_LLM_PROVIDER=openai
python -m careerclaw.briefing --resume-text .careerclaw/resume.txt

# Force deterministic draft even when key is set
python -m careerclaw.briefing --resume-text .careerclaw/resume.txt --no-enhance
```

JSON draft output includes `"enhanced": true | false` per draft.

**Security:** The API key is read from the environment only. It is never
logged, written to disk, or included in any structured output.

---

## Application Tracking

Tracking is written automatically on each non-dry-run. Users can ask
you to update a job's status at any time.

Status progression: `saved` → `applied` → `interview` → `rejected`

To update a status manually, edit `.careerclaw/tracking.json` and
change the `status` field for the relevant `job_id`.

Runtime files (all under `.careerclaw/`, gitignored by default):

| File                        | Contents                                    |
|-----------------------------|---------------------------------------------|
| `profile.json`              | User profile                                |
| `resume.txt` / `resume.pdf` | Resume file (save here on first run)        |
| `tracking.json`             | Saved jobs keyed by `job_id`                |
| `runs.jsonl`                | Append-only run log (one line per run)      |
| `resume_intel.json`         | Cached resume intelligence (auto-generated) |

---

## HN Thread ID — Monthly Update Required

The Hacker News "Who is Hiring?" thread is posted on the first weekday
of each month. The thread ID in `careerclaw/config.py` must be updated
manually each month to get fresh listings.

```python
# careerclaw/config.py
HN_WHO_IS_HIRING_THREAD_ID = 46857488  # Update monthly
```

To find the current thread ID: search
`site:news.ycombinator.com "who is hiring"` and copy the numeric item
ID from the URL (e.g. `https://news.ycombinator.com/item?id=XXXXXXXX`).

If the user reports stale or missing HN results, this is the first thing
to check.

---

## Running Tests

```bash
# All unit and integration tests (offline, no network required)
python -m pytest -q

# Live smoke test (requires network — run before releases only)
python -m scripts.smoke_test_sources
```

---

## Permissions Used

| Permission   | Purpose                                                      |
|--------------|--------------------------------------------------------------|
| `read`       | Read `profile.json`, `tracking.json`, and resume files       |
| `write`      | Write `tracking.json`, `runs.jsonl`, and `resume_intel.json` |
| `exec`       | Run the Python briefing pipeline                             |
| `web_search` | Fetch RemoteOK RSS and HN Firebase API                       |

No backend calls. No telemetry. No credential storage.
External network calls: `remoteok.com` (RSS) and
`hacker-news.firebaseio.com` (public API) only.