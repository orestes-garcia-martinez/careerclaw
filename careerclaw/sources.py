from __future__ import annotations

from typing import List
from careerclaw.models import NormalizedJob
from careerclaw.adapters.remoteok import fetch_remoteok_jobs
from careerclaw.adapters.hackernews import fetch_hn_whos_hiring_jobs_default


def fetch_all_jobs() -> List[NormalizedJob]:
    jobs: List[NormalizedJob] = []
    jobs.extend(fetch_remoteok_jobs())
    jobs.extend(fetch_hn_whos_hiring_jobs_default())
    return jobs
