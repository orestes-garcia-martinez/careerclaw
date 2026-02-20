# Contributing to CareerClaw

Thank you for your interest in contributing. CareerClaw is a small,
actively maintained project and contributions are welcome — but please
read this guide before opening a PR so your effort isn't wasted.

---

## Before You Start

**For bug fixes:** open a GitHub issue first describing the problem and
the proposed fix. For obvious typos or one-line corrections you can skip
this step.

**For new features:** open an issue and wait for a response before
writing code. CareerClaw follows a phase-based roadmap with explicit
scope gates. A feature that looks useful may be deliberately deferred
or out of scope for the current phase.

**For security vulnerabilities:** do not open a public issue. See
[SECURITY.md](SECURITY.md) for the responsible disclosure process.

---

## Development Setup

```bash
git clone https://github.com/orestes-garcia-martinez/careerclaw
cd careerclaw

# Create and activate a virtual environment
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

Verify the setup:

```bash
python -m pytest -q
```

All tests must pass before you write a single line of changes.

---

## Branch Workflow

| Branch           | Purpose                                              |
|------------------|------------------------------------------------------|
| `main`           | Stable, tagged releases only. Never commit directly. |
| `dev`            | Active development target. All PRs merge here.       |
| `feature/<name>` | Your working branch, created from `dev`.             |

```bash
# Start from the latest dev
git checkout dev
git pull origin dev

# Create your feature branch
git checkout -b feature/your-change-name

# When ready, open a PR targeting dev — not main
```

PRs targeting `main` directly will be closed.

---

## Making Changes

### Code style

- Match the existing style. CareerClaw uses no linter or formatter yet,
  so read the surrounding code before writing new code.
- Use explicit, readable code over clever abstractions.
- Add docstrings to public functions. One-line docstrings are fine for
  simple helpers.
- Use `from __future__ import annotations` at the top of every module
  (already the pattern throughout).

### Module layering

Respect the dependency layer rule — higher layers may import lower, but
never the reverse:

1. `careerclaw/core/` — shared text processing, utilities
2. `careerclaw/matching/`, `careerclaw/resume_intel.py` — domain logic
3. `careerclaw/adapters/`, `careerclaw/io/` — I/O and adapters
4. `careerclaw/tracking.py` — persistence
5. `careerclaw/briefing.py` — orchestration and CLI (nothing imports this)

If your change requires importing `briefing.py` from a lower layer,
the design needs to be reconsidered.

### Changing behavior

If your change alters existing behavior (not just adds new behavior),
update the relevant tests to reflect the new contract. Do not delete
tests to make your change pass.

---

## Testing

All tests run offline. No network access is required or permitted in
the unit or contract test suites.

```bash
# Run all tests
python -m pytest -q

# Run a specific file
python -m pytest tests/unit/test_matching_engine.py -q

# Run tests matching a keyword
python -m pytest -q -k "salary"

# Live smoke test — requires network, run manually before releases only
python -m scripts.smoke_test_sources
```

### Test requirements

Every PR must include tests. The type of test depends on what changed:

| Change                  | Required test type                                              |
|-------------------------|-----------------------------------------------------------------|
| New scoring logic       | Unit test in `tests/unit/`                                      |
| New or modified adapter | Contract test in `tests/contract/` using an offline fixture     |
| New pipeline behavior   | Integration test in `tests/unit/test_briefing_orchestration.py` |
| New stopword            | Unit test verifying the term is filtered                        |
| Bug fix                 | Regression test that would have caught the original bug         |

### Writing tests

**Use fixtures from `conftest.py`** rather than reading files inline:

```python
# Good — uses shared fixtures
def test_something(load_json):
    data = load_json("hn_comment_1.json")
```

# Avoid it — duplicates file reading logic
```python
def test_something():
    data = json.loads(Path("tests/fixtures/hn_comment_1.json").read_text())
```

**Mock network calls** in contract tests using `monkeypatch`:

```python
def test_remoteok_adapter(monkeypatch, load_text):
    xml = load_text("remoteok_sample.xml")
    monkeypatch.setattr("careerclaw.adapters.remoteok._fetch_rss", lambda: xml)
    jobs = remoteok_adapter.fetch_jobs()
    assert len(jobs) > 0
```

**Use the `assert_normalized_job_contract()` helper** in
`tests/contract/test_adapters.py` when testing adapter output — it
validates all `NormalizedJob` invariants in one call.

**Never add tests that require `CAREERCLAW_LLM_KEY`** to be set. LLM
tests use mocked responses. The CI workflow explicitly unsets the key
to enforce this.

---

## Adding a New Job Source

New job source adapters are a common contribution. Before writing code:

1. Confirm the source is publicly accessible without authentication
2. Confirm the source's terms of service permit automated access
3. Open an issue — new sources may be deferred to a specific PR milestone

If approved, the pattern to follow:

1. Add the adapter in `careerclaw/adapters/your_source.py`
2. Implement `fetch_jobs() -> list[NormalizedJob]`
3. Normalize all output to `NormalizedJob` — no source-specific fields
   should leak past the adapter boundary
4. Add the source to `careerclaw/sources.py` wrapped in a `try/except`
   so a single source failure does not break the full pipeline
5. Add a config entry in `careerclaw/config.py`
6. Add a real fixture file to `tests/fixtures/`
7. Add offline contract tests in `tests/contract/test_adapters.py`
8. Update the smoke test to include the new source

---

## Commit Messages

Use short, descriptive imperative sentences:

```
Fix salary scoring when job_max is None
Add stopwords: apply, candidate, competitive
Extend ResumeIntelligence to accept target_roles
```

Do not use commit messages like `fix bug`, `update`, or `changes`.

One logical change per commit. If your PR fixes two unrelated things,
split them into two commits (or two PRs).

---

## Pull Request Checklist

Before marking your PR ready for review:

- [ ] All tests pass: `python -m pytest -q`
- [ ] New behavior has test coverage
- [ ] No changes to `.careerclaw/` contents committed
- [ ] No LLM API keys or personal data in any file
- [ ] `CHANGELOG.md` updated under `[Unreleased]` with a concise entry
- [ ] PR targets `dev`, not `main`
- [ ] PR description explains what changed and why

### CHANGELOG format

Follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/):

```markdown
## [Unreleased]

### Fixed
- Brief description of the fix and which file was changed

### Added
- Brief description of the new feature
```

---

## What We Will Not Merge

- Changes that break the offline test suite
- New external dependencies without prior discussion
- Scraping of authenticated or restricted platforms (LinkedIn, Indeed, etc.)
- Features that require a backend server or telemetry endpoint
- Code that stores or logs API keys in any form
- Changes that expand permissions beyond what is documented in `SKILL.md`
- Direct commits to `main`

---

## Questions

Open a GitHub issue with the `question` label. Response target is
within 72 hours.