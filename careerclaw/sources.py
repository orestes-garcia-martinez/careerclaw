from __future__ import annotations

import sys
from typing import List
from careerclaw.models import NormalizedJob
from careerclaw.adapters.remoteok import fetch_remoteok_jobs
from careerclaw.adapters.hackernews import fetch_hn_whos_hiring_jobs_default


def fetch_all_jobs() -> List[NormalizedJob]:
    jobs: List[NormalizedJob] = []
    errors: List[str] = []

    for label, fetcher in [
        ("RemoteOK", fetch_remoteok_jobs),
        ("HN Who's Hiring", fetch_hn_whos_hiring_jobs_default),
    ]:
        try:
            jobs.extend(fetcher())
        except Exception as exc:
            errors.append(f"{label}: {exc}")
            print(f"[CareerClaw] WARNING: {label} fetch failed: {exc}", file=sys.stderr)

    if errors and not jobs:
        raise RuntimeError(f"All sources failed: {'; '.join(errors)}")

    return jobs
