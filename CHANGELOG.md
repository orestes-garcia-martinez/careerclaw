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
