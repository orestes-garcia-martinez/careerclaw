# Changelog

All notable changes to this project will be documented in this file.

The format follows Keep a Changelog and Semantic Versioning.

---
## [Unreleased]

---

## [0.3.0] - 2026-02-17

### Added
- Resume Intelligence layer (`careerclaw/resume_intel.py`): section-aware signal extraction
  from resume summary and optional resume file (`--resume-text`, `--resume-pdf`)
- Job Requirements extraction (`careerclaw/requirements.py`): deterministic keyword and phrase
  signals from job title + description + tags
- Gap Analysis engine (`careerclaw/gap.py`): weighted fit score comparing resume signals to
  job requirements; produces `fit_score`, `fit_score_unweighted`, matched signals, and gaps
- Ordered keyword streams (`keyword_stream`) for both job requirements and resume intelligence,
  preserving first-seen order for deterministic agent-readable output
- Section-aware resume weighting: Skills (1.0) > Summary (0.8) > Experience/Projects (0.7) >
  Education (0.4) > Interests (0.2)
- `UserProfile.skills` and `UserProfile.target_roles` wired into `ResumeIntelligence` as a
  synthetic "Skills" section at weight 1.0 — profile-declared skills are now treated as
  signals in gap analysis, not gaps
- CLI analysis verbosity flag (`--analysis off|summary|full`) for controlling gap output detail
- Gap analysis summary block (`analysis.summary.top_signals` / `analysis.summary.top_gaps`)
  surfaced in CLI and JSON output
- Recruitment boilerplate stopwords in `text_processing._STOPWORDS`: `apply`, `candidate`,
  `interview`, `hiring`, `competitive`, `opportunity`, and 15+ related terms
- Resume loader (`careerclaw/io/resume_loader.py`) supporting `.txt` and `.pdf` inputs
- 12 new unit and integration tests covering resume intelligence, gap analysis, and
  text processing signal hygiene

### Changed
- `build_resume_intelligence()` now accepts optional `skills` and `target_roles` parameters
  (fully backward-compatible; existing callers unchanged)
- `briefing.py` passes `profile.skills` and `profile.target_roles` to resume intelligence
  builder, eliminating signal starvation when no resume file is provided
- Gap analysis keywords and phrases now follow job description order (not alphabetical),
  improving readability in agent contexts
- Resume intelligence keywords preserved in first-seen order

### Fixed
- Profile-declared skills (e.g. `react`, `typescript`, `python`) were incorrectly appearing
  as keyword gaps in gap analysis — now correctly identified as matched signals
- Fit scores of 1–2% caused by signal starvation when only `resume_summary` was available;
  scores now reflect actual profile-to-job overlap (4–41% range observed in validation)

### Notes
- Fit scores remain a relative signal for comparing jobs, not an absolute percentage
- The theoretical ceiling for any real resume against HN job postings is ~40–50% due to
  company names, location tokens, and application boilerplate in the denominator
- Draft engine still uses deterministic templates; LLM-enhanced drafting targeting
  actual resume content is the next Pro-tier feature

### Future Work
- `CorpusCache`: Entropy-based token filtering (IDF) to suppress tokens that appear in
  >80% of fetched jobs. Gated behind `corpus_size >= 50`. Planned after job tracking
  accumulates sufficient data.
- `DraftEnhancer` (Pro): LLM-powered outreach drafts that reference resume content and
  company-specific signals, gated behind paid tier

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