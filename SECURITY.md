# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in CareerClaw, please report it
responsibly. **Do not open a public GitHub issue** for security matters.

**Contact:** orestes.garcia.martinez@gmail.com  
**Subject line:** `[SECURITY] CareerClaw — <brief description>`

Include as much detail as you can:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Affected version(s)

### Response SLA

| Severity                                                  | First response | Resolution target      | Release vehicle        |
|-----------------------------------------------------------|----------------|------------------------|------------------------|
| Critical (data exposure, key leakage)                     | < 24 hours     | < 72 hours             | Immediate patch        |
| High (pipeline hijack, file write outside `.careerclaw/`) | < 48 hours     | < 1 week               | Patch release          |
| Medium / Low                                              | < 1 week       | Next scheduled release | Patch or minor release |

You will receive an acknowledgement within the first response window. If
you do not hear back within 48 hours, follow up directly.

We do not currently offer a bug bounty program, but we will credit
responsible disclosures in the CHANGELOG unless you prefer to remain
anonymous.

---

## Security Architecture

CareerClaw is designed with a local-first, minimal-footprint security
model. The threat surface is intentionally small.

### What runs locally

Everything. CareerClaw has no backend server, no cloud endpoint, and
no telemetry pipeline. All computation — fetching, ranking, drafting,
and persistence — runs on the user's machine.

### External network calls

CareerClaw makes exactly two categories of outbound network requests:

| Destination                                    | Protocol | Auth               | Purpose                    |
|------------------------------------------------|----------|--------------------|----------------------------|
| `remoteok.com/remote-dev-jobs.rss`             | HTTPS    | None               | Job ingestion              |
| `hacker-news.firebaseio.com/v0/item/{id}.json` | HTTPS    | None               | Job ingestion              |
| User's configured LLM provider (optional)      | HTTPS    | User's own API key | Pro draft enhancement only |

No other network calls are made. No analytics endpoints. No version
check beacons. No callback URLs.

### Credential handling

`CAREERCLAW_LLM_KEY` is the only credential CareerClaw ever touches.

- Read from environment variable only — never from a config file or
  argument
- Never written to `tracking.json`, `runs.jsonl`, or any structured
  output
- Never logged to console, even on error
- Sanitized from exception messages before they propagate
- Covered by a dedicated security test in the test suite
  (`tests/unit/test_config.py`) that asserts the key does not appear
  in any structured output field

### Local data

All runtime state is stored under `.careerclaw/` in the working
directory. This folder is included in `.gitignore` by default.

| File                        | Contents                                     | Sensitive?          |
|-----------------------------|----------------------------------------------|---------------------|
| `profile.json`              | Skills, roles, experience, salary range      | Yes — do not commit |
| `resume.txt` / `resume.pdf` | Full resume text                             | Yes — do not commit |
| `tracking.json`             | Job IDs and application statuses             | Moderate            |
| `runs.jsonl`                | Anonymous run metrics (job counts, duration) | No                  |
| `resume_intel.json`         | Extracted keyword cache                      | No                  |

**Never commit `.careerclaw/` to version control.** The `.gitignore`
entry is present by default, but verify it before pushing.

### Source code transparency

- No obfuscated code
- No Base64-encoded URLs or network targets
- No minified scripts
- No post-install hooks that execute network calls
- All dependencies declared explicitly in `pyproject.toml`

Every release is scanned with VirusTotal before publishing to ClawHub.

### Permissions

CareerClaw requests only the permissions it actually uses:

| Permission   | Used for                                           |
|--------------|----------------------------------------------------|
| `read`       | `profile.json`, `tracking.json`, resume files      |
| `write`      | `tracking.json`, `runs.jsonl`, `resume_intel.json` |
| `exec`       | Running the Python pipeline                        |
| `web_search` | Fetching RemoteOK RSS and HN Firebase API          |

No `notification`, `cron`, or elevated permissions are requested in
the free tier.

---

## Known Limitations

**HN thread ID is manually maintained.** The Hacker News "Who is
Hiring?" thread ID in `careerclaw/config.py` must be updated monthly.
An outdated ID will result in stale or missing results, not a security
issue — but worth noting for transparency.

**Resume text is stored in plaintext.** `.careerclaw/resume.txt` is
unencrypted. Users in shared environments should ensure appropriate
filesystem permissions on the `.careerclaw/` directory.

**LLM provider data handling.** When `CAREERCLAW_LLM_KEY` is set,
job description excerpts and resume signal keywords are sent to the
configured provider (Anthropic or OpenAI). CareerClaw never sends the
full resume text to any LLM — only the extracted keyword signals from
`ResumeIntelligence`. Review your provider's data handling policy if
this is a concern.

---

## Supported Versions

Security fixes are applied to the latest release only. We do not
backport fixes to older versions.

| Version              | Supported |
|----------------------|-----------|
| Latest (main branch) | ✅         |
| Older releases       | ❌         |