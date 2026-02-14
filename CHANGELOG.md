# Changelog

All notable changes to this project will be documented in this file.

The format is inspired by Keep a Changelog and follows semantic versioning principles.

---

## [0.1.0] - 2026-02-13

### Added
- Centralized configuration via `careerclaw/config.py`
- RemoteOK RSS adapter
- Hacker News “Who is hiring?” adapter
- Canonical `NormalizedJob` schema
- Instrumentation primitive: `BriefingRun`
- Source aggregation layer
- Smoke test script for source validation
- Branch workflow: main / dev strategy

### Notes
- HN thread ID is manually configured in MVP.
- Company/title parsing heuristics are best-effort.
- HTML decoding improvements deferred.

## [0.1.1] - 2026-02-13

### Added
- Deterministic matching engine package (`careerclaw/matching/`) with explainable scoring breakdown
- Unit tests for matching engine and scoring
- Adapter contract tests with offline fixtures (RemoteOK RSS XML, HN JSON)

### Changed
- Moved adapters into `careerclaw/adapters/` for consistent package imports
- Added `pytest` to `requirements.txt`
