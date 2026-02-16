
---

# ✅ CHANGELOG.md

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format follows Keep a Changelog and Semantic Versioning.

---

## [0.2.0] - 2026-02-16

### Added
- Phase 4: Daily Briefing orchestration (`python -m careerclaw.briefing`)
- Profile loading from JSON file for CLI usage
- Local runtime persistence under `.careerclaw/`
  - `tracking.json`
  - `runs.jsonl`
- Dry-run mode (`--dry-run`)
- JSON output mode (`--json`)
- Hacker News HTML sanitation (entity decoding + safer tag stripping)
- Phase 4 unit and integration tests
- Packaging via `pyproject.toml`
- Editable install support (`pip install -e .`)

### Changed
- Briefing now consumes `ScoredJob` dataclass from matching engine
- Ranking explanations surfaced in CLI output
- Skill matching improved to reduce false positives

### Notes
- `.careerclaw/` directory is runtime-only and must be gitignored
- Salary normalization still expected at ingestion stage
- HN thread ID remains manually configured in MVP

---

## [0.1.1] - 2026-02-13

### Added
- Deterministic matching engine package (`careerclaw/matching/`)
- Explainable scoring breakdown
- Unit tests for matching engine and scoring
- Adapter contract tests with offline fixtures

### Changed
- Adapters moved into `careerclaw/adapters/`
- Added `pytest` to development dependencies

---

## [0.1.0] - 2026-02-13

### Added
- Centralized configuration
- RemoteOK RSS adapter
- Hacker News “Who is hiring?” adapter
- Canonical `NormalizedJob` schema
- Instrumentation primitive: `BriefingRun`
- Source aggregation layer
- Smoke test script
- Branch workflow: main / dev strategy

### Notes
- Company/title parsing heuristics are best-effort
- HTML decoding improvements deferred (completed in 0.1.2)
