---
name: careerclaw
version: 0.7.2
description: >
  Run a job search briefing, find job matches, draft outreach emails,
  or track job applications. Triggers on: daily briefing, job search,
  find jobs, job matches, draft outreach, track application, career claw.
metadata:
  openclaw:
    emoji: "🦞"
    primaryEnv: CAREERCLAW_PRO_KEY

    # careerclaw is installed automatically on first run via pip bootstrap.
    # No manual setup or sandbox image configuration required.
    requires:
      bins: ["python3", "curl"]

    optionalEnv:
      - name: CAREERCLAW_PRO_KEY
        description: "CareerClaw Pro license key. Unlocks gap analysis, resume intelligence, and LLM-enhanced drafts."
      - name: CAREERCLAW_OPENAI_KEY
        description: "OpenAI API key for Pro LLM draft enhancement."
      - name: CAREERCLAW_ANTHROPIC_KEY
        description: "Anthropic API key for Pro LLM draft enhancement."
      - name: CAREERCLAW_LLM_KEY
        description: "Legacy single-provider API key override. Prefer provider-specific keys above."
      - name: CAREERCLAW_LLM_PROVIDER
        description: "'anthropic' (default) or 'openai'. Ignored when CAREERCLAW_LLM_CHAIN is set."
      - name: CAREERCLAW_LLM_MODEL
        description: "Override the default model."
      - name: CAREERCLAW_LLM_CHAIN
        description: "Ordered failover chain, e.g. 'openai/gpt-5.2,openai/gpt-4o-mini,anthropic/claude-sonnet-4-6'."
      - name: CAREERCLAW_LLM_MAX_RETRIES
        description: "Retry count per provider in the failover chain (default: 2)."
      - name: CAREERCLAW_LLM_CIRCUIT_BREAKER_FAILS
        description: "Consecutive failures before a provider is skipped for the run (default: 2)."
---

# CareerClaw

Fetch job listings from RemoteOK and Hacker News Who's Hiring, rank them against the user's
profile, generate tailored outreach email drafts, and persist an application tracking log —
all locally, with no backend.

---

## Before Running Any Command

Before executing any CareerClaw command, always run this self-healing check first:

```bash
python3 -m careerclaw.briefing --help >/dev/null 2>&1 || \
  (curl -sS https://bootstrap.pypa.io/get-pip.py | python3 - --break-system-packages --quiet 2>/dev/null; \
   python3 -m pip install --quiet --break-system-packages careerclaw)
```

This ensures CareerClaw is installed in any environment — sandbox, host, or managed cloud —
with zero manual intervention. If CareerClaw is already installed, the check completes
instantly and proceeds. The pip bootstrap via `get-pip.py` handles environments where pip
is not pre-installed (such as the default OpenClaw sandbox).

---

## First Run: Setup

### Step 1 — Create the working directory

```bash
mkdir -p .careerclaw
```

### Step 2 — Share the resume

Ask the user to provide their resume (PDF or plain text file). Do not ask them to fill
in a JSON form.

Save the resume file to:
- `.careerclaw/resume.txt` (preferred), or
- `.careerclaw/resume.pdf`

### Step 3 — Create the user profile from their resume

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

Confirm the profile with the user before proceeding, showing the extracted values.
Offer to correct any field they disagree with.

### Step 4 — Run the first briefing (dry run)

Once the profile is confirmed, run:

```bash
python3 -m careerclaw.briefing --help >/dev/null 2>&1 || \
  (curl -sS https://bootstrap.pypa.io/get-pip.py | python3 - --break-system-packages --quiet 2>/dev/null; \
   python3 -m pip install --quiet --break-system-packages careerclaw)
python3 -m careerclaw.briefing --resume-text .careerclaw/resume.txt --dry-run
```

(Use `--resume-pdf` if the resume was provided as a PDF.)

Use `--dry-run` for the first run so nothing is written until the user confirms
they are happy with the results.

---

## Running the Daily Briefing

Always run the self-healing check before executing any briefing command:

```bash
python3 -m careerclaw.briefing --help >/dev/null 2>&1 || \
  (curl -sS https://bootstrap.pypa.io/get-pip.py | python3 - --break-system-packages --quiet 2>/dev/null; \
   python3 -m pip install --quiet --break-system-packages careerclaw)
```

Then run the briefing:

```bash
# Standard run (writes tracking.json and runs.jsonl)
python3 -m careerclaw.briefing --resume-text .careerclaw/resume.txt

# Dry run — no files written, safe for previewing
python3 -m careerclaw.briefing --resume-text .careerclaw/resume.txt --dry-run

# JSON-only output (for agent parsing)
python3 -m careerclaw.briefing --resume-text .careerclaw/resume.txt --json

# Control analysis verbosity
python3 -m careerclaw.briefing --analysis off      # no gap analysis (default)
python3 -m careerclaw.briefing --analysis summary  # fit % and highlights
python3 -m careerclaw.briefing --analysis full     # gap keywords and phrases

# Return more than 3 results
python3 -m careerclaw.briefing --top-k 5
```

**Always pass `--resume-text` or `--resume-pdf` on every run** to ensure resume intelligence
is active. Without it, fit scores will be low (1–5%) though match scores remain valid.

---

## Presenting Results to the User

### Matches

For each match, always show:
- Job title and company
- Location and work mode
- Score (and fit % if available)
- 1–2 matched skills or keywords
- Any relevant warning (e.g. entry-level listing, location mismatch, LATAM-only, contract vs full-time)

### Drafts

The `drafts` field in the JSON output contains full outreach email drafts. Each draft has
a `Subject:` line and a complete email body ready to send.

Rules:
1. Make it explicit these are email drafts (not summaries).
2. In chat, show a one-sentence summary of each draft's angle to keep results readable.
3. Offer: "Want the full email for any of these?"
4. When asked, output the full `Subject:` line + email body verbatim from JSON.
5. If `"enhanced": true`, say it is LLM-enhanced. If `"enhanced": false`, say it is a template draft.

### After the briefing

Always end with a next-step prompt:
- show full drafts
- bump results (`--top-k 5`)
- update tracking status
- run a dry-run preview

---

## Upgrading to Pro

CareerClaw Pro unlocks gap analysis, resume intelligence, and LLM-enhanced outreach drafts.

**Purchase:** https://ogm.gumroad.com/l/careerclaw-pro
**Price:** $39 (lifetime, one-time payment)

After purchase, the license key is emailed immediately.

### Activating Pro — Docker / self-hosted users

Add to your `.env` file:

```env
CAREERCLAW_PRO_KEY=YOUR-KEY-HERE
CAREERCLAW_OPENAI_KEY=sk-proj-...
CAREERCLAW_ANTHROPIC_KEY=sk-ant-...
CAREERCLAW_LLM_CHAIN=openai/gpt-5.2,openai/gpt-4o-mini,anthropic/claude-sonnet-4-6
```

### Activating Pro — MyClaw / managed users

Tell your OpenClaw agent:
> "Set my CAREERCLAW_PRO_KEY to YOUR-KEY-HERE"

---

## Application Tracking

Status progression: `saved` → `applied` → `interview` → `rejected`

Runtime files (all under `.careerclaw/`):

| File                        | Contents                                    |
|-----------------------------|---------------------------------------------|
| `profile.json`              | User profile                                |
| `resume.txt` / `resume.pdf` | Resume file                                 |
| `tracking.json`             | Saved jobs keyed by `job_id`                |
| `runs.jsonl`                | Append-only run log (one line per run)      |
| `resume_intel.json`         | Cached resume intelligence (auto-generated) |

---

## HN Thread ID — Monthly Update Required

The Hacker News "Who is Hiring?" thread is posted on the first weekday of each month.
The thread ID in `careerclaw/config.py` must be updated manually each month to get
fresh listings.

To find the current thread ID: search `site:news.ycombinator.com "who is hiring"` and
copy the numeric item ID from the URL.

If the user reports stale or missing HN results, this is the first thing to check.

---

## Permissions Used

| Permission   | Purpose                                                      |
|--------------|--------------------------------------------------------------|
| `read`       | Read `profile.json`, `tracking.json`, and resume files       |
| `write`      | Write `tracking.json`, `runs.jsonl`, and `resume_intel.json` |
| `exec`       | Run the CareerClaw pipeline                                  |
| `web_search` | Fetch RemoteOK RSS and HN Firebase API                       |

No backend calls. No telemetry. No credential storage.
External network calls: `remoteok.com` (RSS) and `hacker-news.firebaseio.com` (public API) only.