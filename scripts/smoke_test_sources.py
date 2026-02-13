from __future__ import annotations

import sys
from pprint import pprint

from careerclaw import config
from adapters.remoteok import fetch_remoteok_jobs
from adapters.hackernews import fetch_hn_whos_hiring_jobs_default


def main() -> int:
    # --- Preflight ---
    if not config.HN_WHO_IS_HIRING_THREAD_ID or config.HN_WHO_IS_HIRING_THREAD_ID <= 0:
        print("ERROR: Set HN_WHO_IS_HIRING_THREAD_ID in careerclaw/config.py")
        return 2

    print("=== CareerClaw Smoke Test: Sources ===")
    print(f"RemoteOK RSS: {config.REMOTEOK_RSS_URL}")
    print(f"HN Thread ID: {config.HN_WHO_IS_HIRING_THREAD_ID}")
    print("")

    # --- RemoteOK ---
    print(">>> Fetching RemoteOK jobs...")
    remote_jobs = fetch_remoteok_jobs(limit=5)
    print(f"RemoteOK returned: {len(remote_jobs)}")
    if remote_jobs:
        print("RemoteOK sample:")
        pprint(remote_jobs[0].to_dict())
    print("")

    # --- Hacker News ---
    print(">>> Fetching Hacker News 'Who is hiring?' jobs...")
    hn_jobs = fetch_hn_whos_hiring_jobs_default(limit_comments=25)
    print(f"HN returned: {len(hn_jobs)}")
    if hn_jobs:
        print("HN sample:")
        pprint(hn_jobs[0].to_dict())
    print("")

    # --- Basic schema assertions ---
    print(">>> Running basic schema assertions...")
    for j in (remote_jobs[:2] + hn_jobs[:2]):
        assert j.job_id and isinstance(j.job_id, str)
        assert j.title and j.company and j.description
        assert j.source in (j.source.__class__.REMOTEOK, j.source.__class__.HN_WHO_IS_HIRING)
    print("OK ✅")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
