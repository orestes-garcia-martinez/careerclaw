# Changelog

All notable changes to this project will be documented in this file.

The format follows Keep a Changelog and Semantic Versioning.

---

## [unreleased]

---

## [0.7.1] - 2026-02-26

### Changed
- Migrated Pro license validation from Polar.sh to Gumroad
  (`careerclaw/license.py`). Replaced separate activate/validate API
  calls with Gumroad's single `/v2/licenses/verify` endpoint.
- Revalidation calls now set `increment_uses_count=false` to avoid
  burning customer usage quota on routine 7-day rechecks.
- Updated buy link to `https://ogm.gumroad.com/l/careerclaw-pro` in
  `README.md`.

### Fixed
- Removed dependency on Polar activation IDs (`activation_id`) from
  cache schema; cache now stores only `key_hash`, `valid`, and
  `validated_at`.

### Security
- Pro license key is never written to disk; only SHA-256 hash cached.
  Gumroad Product ID is a public identifier and safe to commit.

---

## [0.7.0] - 2026-02-24

### Added
- Production-grade LLM draft enhancement failover chain via `CAREERCLAW_LLM_CHAIN` (provider/model candidates).
- Retry + circuit breaker controls for the draft enhancer (`CAREERCLAW_LLM_MAX_RETRIES`, `CAREERCLAW_LLM_CIRCUIT_BREAKER_FAILS`).
- README “LLM Architecture” section explaining Agent Layer (OpenClaw) vs Draft Layer (CareerClaw Pro).

### Changed
- Clean separation of provider keys:
  - OpenClaw agent layer uses `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`.
  - CareerClaw draft layer optionally uses `CAREERCLAW_LLM_KEY` and otherwise reuses provider keys.
- Updated `.env.example` and `docker-compose.yml` comments to reflect the provider-specific key architecture and failover config.
- Draft enhancement now degrades safely to deterministic drafts when LLM enhancement fails (auth/provider/transient errors).

### Docs
- Updated local Docker/OpenClaw testing guidance (Telegram workflow + sandbox configuration) for reproducible end-to-end runs.

---

## [0.6.0] - 2026-02-23

### Added
- careerclaw/license.py: activate/validate against LemonSqueezy API
  with 7-day cache and 24h grace period on network failure
- careerclaw/config.py: add CAREERCLAW_PRO_KEY env var and pro_licensed()
- careerclaw/briefing.py: gate gap analysis, resume intel, and LLM
  drafts behind pro_licensed()
- .env.example + SKILL.md: document CAREERCLAW_PRO_KEY with purchase
  URL and MyClaw activation instructions
- tests/unit/test_license.py: 15 unit tests (no network)
- scripts/smoke_test_license.py: end-to-end activation smoke test"
  git push origin feat/pro-license-gate

---

## [0.5.0] - 2026-02-22

### Added
- `Dockerfile.sandbox` extending `openclaw-sandbox:bookworm-slim` with
  Python 3.12, CareerClaw, `anthropic`, and `openai` for isolated local
  agent testing.
- `docker/docker-compose.yml` wiring the OpenClaw gateway and CareerClaw
  sandbox with controlled `.careerclaw/` volume mount and bridge network.
- `docker/openclaw.yml` agent sandbox configuration (mode, tools,
  workspace access).
- `.env.example` documenting all required environment variables.
- `DOCKER.md` step-by-step local setup guide covering WSL2, Docker
  Desktop, Telegram bot creation, volume permissions, and sandbox env
  var configuration.

### Changed
- `SKILL.md`: Added "Presenting Results to the User" section instructing
  the agent to always label outreach drafts as email drafts, show a
  one-sentence summary per draft in chat interfaces, offer to display
  the full email on request, indicate LLM-enhanced vs template status
  per draft, and confirm dry-run vs real run at the end of every
  briefing.

---

## [0.4.3] - 2026-02-18

### Fixed
- **`https` stopword** (`careerclaw/core/text_processing.py`): Added `https`, `http`, `www`,
  `linkedin`, and `github` to the stopword set. These tokens appeared in gap analysis keyword
  lists when resume text included LinkedIn/GitHub URLs in the header section.
- **HN description-as-title** (`careerclaw/adapters/hackernews.py`): `_pick_role()` now skips
  pipe segments longer than 80 chars after URL stripping. Fixes the Doowii post where the
  company description sentence ("Doowii is building an AI operating layer...") was picked as
  the job title because it contained role keywords ("ai", "platform").

---

## [0.4.2] - 2026-02-18

### Fixed
- **Anti-hallucination** (`careerclaw/llm/prompt.py`): Added explicit CRITICAL instruction in
  both system prompt and requirements block prohibiting the LLM from inventing metrics,
  percentages, project names, or achievements not present in the provided resume signals.
  Addresses fabricated stat ("reduced API calls by 40%") observed in Starbridge draft during
  live testing.
- **HN title URL stripping** (`careerclaw/adapters/hackernews.py`): Company/title parser now
  strips leading URLs (e.g. `https://doowii.io`) from the first pipe-delimited segment before
  assigning the company name. Fixes malformed titles and prevents URL tokens from polluting
  LLM prompt context (root cause of the fabricated Doowii education background).

### Changed
- **Configurable LLM model** (`careerclaw/config.py`, `careerclaw/llm/enhancer.py`):
  Added `CAREERCLAW_LLM_MODEL` env var. Defaults to `claude-sonnet-4-6` for Anthropic and
  `gpt-4o-mini` for OpenAI. Haiku is no longer the hardcoded default — Sonnet 4.6 produces
  meaningfully better drafts at still-negligible cost (~$0.018/run) at the user's own key.
  Override with `$env:CAREERCLAW_LLM_MODEL = "claude-haiku-4-5-20251001"` if cost matters.

### Added
- 3 new unit tests for `CAREERCLAW_LLM_MODEL` behavior (default per provider, env override)

---

## [0.4.1] - 2026-02-18

### Changed
- **Audience-agnostic outreach** — CareerClaw now serves candidates in any profession, not
  just software engineering
- LLM system prompt (`careerclaw/llm/prompt.py`): role changed from "senior software engineer"
  to "career advisor"; removed "technical" framing; added explicit note that the candidate may
  be in any field (technology, healthcare, education, finance, trades, or any other profession)
- LLM prompt builder: fallback job title changed from `"Software Engineer"` to `"the position"`;
  "technical signals" wording changed to "professional signals"
- Deterministic draft template (`careerclaw/drafting.py`): replaced three software-specific
  bullet points with profession-neutral equivalents that apply to any field
- Default fallback profile (`careerclaw/briefing.py`): replaced tech-stack example with
  generic placeholder suitable for any candidate

### Scope Decision — PR-7 Job Sources
PR-7 will implement adapters for **Greenhouse/Lever public boards** and **Wellfound** only.
Stack Overflow Jobs (developer-only) is dropped from scope. RemoteOK API v2 is deferred
until post-launch. Rationale: Greenhouse/Lever covers healthcare, education, finance, and
other non-tech industries — essential for a truly audience-agnostic skill.

---

## [0.4.0] - 2026-02-18

### Added
- **Pro Tier: LLM Draft Enhancer** (`careerclaw/llm/`): optional Anthropic and OpenAI-backed
  outreach draft personalisation, activated when `CAREERCLAW_LLM_KEY` is set in the environment
- `careerclaw/llm/enhancer.py`: `LLMDraftEnhancer` with 10-second hard timeout, word-count
  validation (50–350 words), and graceful fallback to deterministic draft on any failure
- `careerclaw/llm/prompt.py`: prompt builder assembling job context, gap analysis signals, and
  resume highlights into a <600-token input targeting 150–200 word personalised output
- `DraftResult.enhanced: bool` field — `true` when the draft was produced by the LLM enhancer
- `GapAnalysis` object stored on `RankedMatch.gap` for use by the prompt builder without
  recomputing gap analysis per draft
- `--no-enhance` CLI flag: forces deterministic drafts even when `CAREERCLAW_LLM_KEY` is set
- `CAREERCLAW_LLM_KEY` and `CAREERCLAW_LLM_PROVIDER` environment variable support in
  `careerclaw/config.py` with `llm_configured()` helper
- `enhanced: true|false` field emitted on each draft object in JSON output

### Changed
- `run_daily_briefing()` accepts new `no_enhance: bool` parameter (default `False`)
- CLI draft output shows `[LLM enhanced]` tag when enhancement is active

### Security
- `CAREERCLAW_LLM_KEY` is read from environment only; never logged, never written to
  `tracking.json`, `runs.jsonl`, or any structured output — enforced by dedicated security test

### Future Work
- CorpusCache: Entropy-based token filtering (IDF) to suppress tokens that appear in >80% of
  fetched jobs. Gated behind `corpus_size >= 50`. Planned for a future PR after job tracking
  accumulates sufficient data.

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