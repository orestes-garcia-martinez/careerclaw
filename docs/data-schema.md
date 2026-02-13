# CareerClaw Data Schema (MVP v0.1)

This document defines the canonical data contract for CareerClaw.

All adapters, matching logic, drafting, tracking, and briefing layers must conform to these structures.

---

# 1. NormalizedJob (Canonical Job Record)

This is the single internal job representation used across the system.

All source adapters (RemoteOK, Hacker News) MUST output this shape.

## Required Fields

- source (JobSource)
- title (string)
- company (string)
- description (string)
- job_id (string, stable hash)

## Optional Fields

- location (string | null)
- tags (string[])
- posted_at (datetime | null, UTC)
- canonical_url (string | null)
- source_ref (string | null)

### Field Notes

- `job_id` is a stable hash generated from:
    - source
    - canonical_url (if present)
    - title
    - company
    - posted_at (date portion)

- `source_ref` stores original source identifiers:
    - Hacker News: item id
    - RemoteOK: slug or job id

- `posted_at` must be normalized to UTC if present.

---

# 2. UserProfile (MVP)

Represents the user’s targeting and matching preferences.

## Required Fields

- skills (string[])
- target_roles (string[])
- experience_years (integer)
- work_mode (enum: remote | onsite | hybrid)
- resume_summary (string)

## Optional Fields

- location (string | null)
- salary_min (integer | null)
- salary_max (integer | null)

### Normalization Rules

- Skills and roles must be trimmed and normalized.
- Resume summary must be whitespace-cleaned.
- work_mode must be one of the allowed enum values.

---

# 3. TrackingEntry (Application Tracking)

Represents a persisted record of user interaction with a job.

## Required Fields

- job_id (string)
- status (ApplicationStatus)
- saved_at (datetime UTC)

## Optional Fields

- applied_at (datetime UTC | null)
- notes (string | null)
- next_action_date (date | null)

### Status Flow (MVP)

saved → applied → interview → rejected

No backward transitions required in MVP.

---

# 4. BriefingRun (Instrumentation)

Used to measure workflow stickiness and repeat usage.

## Fields

- user_id (string)
- ran_at (datetime UTC)

### Purpose

Used to measure:

- Total briefing runs
- Users running briefing 2+ times
- Retention signal for Pro-tier validation

---

# 5. Enums

## JobSource

- remoteok
- hn_who_is_hiring

## ApplicationStatus

- saved
- applied
- interview
- rejected

---

# 6. System Invariants

These rules must always hold true:

1. All adapters must output NormalizedJob.
2. No downstream layer may rely on raw source data.
3. job_id must be stable across runs.
4. All timestamps must be UTC.
5. No personal credentials are stored anywhere in the schema.

---

# 7. Versioning

Schema Version: v0.1  
Changes to this document require:

- CHANGELOG update
- Explicit migration note (if breaking)
- Semantic version bump if required
