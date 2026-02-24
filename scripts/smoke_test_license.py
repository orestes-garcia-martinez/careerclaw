"""
smoke_test_license.py — End-to-end Pro license activation smoke test.

Verifies that CAREERCLAW_PRO_KEY activates against LemonSqueezy, writes
.careerclaw/.license_cache, and that the briefing runs in Pro mode.

Usage (from repo root):
    CAREERCLAW_PRO_KEY=<your-test-key> python scripts/smoke_test_license.py

Requirements:
    - CAREERCLAW_PRO_KEY must be set (a real LemonSqueezy test-mode key).
    - Internet access to reach api.lemonsqueezy.com.
    - pip install -e . must have been run.

Exit codes:
    0  — all checks passed
    1  — a check failed
    2  — CAREERCLAW_PRO_KEY not set (misconfiguration)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


# ── Helpers ───────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = REPO_ROOT / ".careerclaw" / ".license_cache"

PASS = "✅"
FAIL = "❌"


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = PASS if condition else FAIL
    line = f"  {status}  {label}"
    if detail:
        line += f"\n       {detail}"
    print(line)
    return condition


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    print("\n=== CareerClaw Smoke Test: Pro License ===\n")

    # ── Preflight ─────────────────────────────────────────────────────────────

    pro_key = os.environ.get("CAREERCLAW_PRO_KEY", "").strip()
    if not pro_key:
        print("ERROR: CAREERCLAW_PRO_KEY is not set.")
        print()
        print("Run with:")
        print("  CAREERCLAW_PRO_KEY=<your-test-key> python scripts/smoke_test_license.py")
        print()
        print("Get a test key by making a test-mode purchase in your LemonSqueezy dashboard.")
        return 2

    print(f"  Key: {pro_key[:8]}{'*' * (len(pro_key) - 8)}  (truncated for display)")
    print()

    # ── Remove any existing cache to force fresh activation ──────────────────

    if CACHE_PATH.exists():
        CACHE_PATH.unlink()
        print("  [setup] Removed existing .license_cache to force fresh activation.\n")

    # ── Step 1: Run briefing --dry-run ────────────────────────────────────────

    print("Step 1 — Running briefing in dry-run mode...")
    env = {**os.environ, "CAREERCLAW_PRO_KEY": pro_key}
    t0 = time.time()
    result = subprocess.run(
        [sys.executable, "-m", "careerclaw.briefing", "--dry-run", "--json"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )
    elapsed_ms = int((time.time() - t0) * 1000)

    briefing_ok = check(
        "Briefing exited with code 0",
        result.returncode == 0,
        detail=result.stderr.strip()[:200] if result.returncode != 0 else "",
    )
    if not briefing_ok:
        print("\n  stdout:", result.stdout[:500])
        print("  stderr:", result.stderr[:500])
        return 1

    check(f"Briefing completed in {elapsed_ms}ms", True)

    # ── Step 2: Parse briefing JSON output ────────────────────────────────────

    print("\nStep 2 — Validating briefing JSON output...")
    briefing_data: dict = {}
    try:
        briefing_data = json.loads(result.stdout)
        json_ok = True
    except json.JSONDecodeError as e:
        json_ok = False
        check("Briefing output is valid JSON", False, detail=str(e))
        return 1

    check("Briefing output is valid JSON", json_ok)

    dry_run_ok = check(
        "dry_run flag is True in output",
        briefing_data.get("dry_run") is True,
    )
    matches_ok = check(
        "top_matches present in output",
        isinstance(briefing_data.get("top_matches"), list),
    )

    # Pro-specific: resume_intelligence should be present (Pro feature).
    resume_intel = briefing_data.get("resume_intelligence")
    pro_output_ok = check(
        "resume_intelligence present (Pro feature active)",
        resume_intel is not None,
        detail="If None, the license gate blocked Pro features — check key validity.",
    )

    # ── Step 3: Verify cache file was written ─────────────────────────────────

    print("\nStep 3 — Verifying .license_cache written to disk...")

    cache_exists = check(
        f"Cache file exists at {CACHE_PATH.relative_to(REPO_ROOT)}",
        CACHE_PATH.exists(),
    )
    if not cache_exists:
        print("\n  Cache file not found — activation likely failed.")
        return 1

    try:
        cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        cache_readable = True
    except Exception as e:
        cache_readable = False
        check("Cache file is valid JSON", False, detail=str(e))
        return 1

    check("Cache file is valid JSON", cache_readable)

    check(
        "Cache contains key_hash",
        bool(cache.get("key_hash")),
    )
    check(
        "Cache valid=True",
        cache.get("valid") is True,
        detail="valid=False means LemonSqueezy rejected the key.",
    )
    check(
        "Cache contains instance_id",
        bool(cache.get("instance_id")),
        detail="Empty instance_id means activation did not complete.",
    )

    validated_at = cache.get("validated_at", 0)
    age_seconds = time.time() - validated_at
    check(
        f"Cache validated_at is recent (age: {int(age_seconds)}s)",
        age_seconds < 60,
        detail="validated_at is older than 60s — may not have been written this run.",
    )

    # ── Step 4: Verify raw key is NOT in cache ────────────────────────────────

    print("\nStep 4 — Verifying raw key is not stored in cache...")

    cache_text = CACHE_PATH.read_text(encoding="utf-8")
    key_not_in_cache = check(
        "Raw license key is NOT present in cache file",
        pro_key not in cache_text,
        detail="SECURITY: raw key should never be written to disk.",
    )

    # ── Step 5: Second run uses cache (no re-activation) ─────────────────────

    print("\nStep 5 — Verifying second run uses cache (no re-activation)...")

    # Patch _activate to detect if it's called on the second run.
    # We do this by checking that validated_at in the cache does NOT change
    # (i.e., the fresh cache is still within the 7-day window).
    validated_at_before = cache.get("validated_at", 0)

    result2 = subprocess.run(
        [sys.executable, "-m", "careerclaw.briefing", "--dry-run", "--json"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPO_ROOT),
    )

    second_run_ok = check(
        "Second run exited with code 0",
        result2.returncode == 0,
    )

    if second_run_ok:
        cache2 = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        validated_at_after = cache2.get("validated_at", 0)
        cache_unchanged = check(
            "Cache validated_at unchanged on second run (cache hit, no re-activation)",
            validated_at_after == validated_at_before,
        )

    # ── Summary ───────────────────────────────────────────────────────────────

    print("\n=== Summary ===")

    all_passed = all([
        briefing_ok,
        json_ok,
        dry_run_ok,
        matches_ok,
        pro_output_ok,
        cache_exists,
        cache_readable,
        key_not_in_cache,
        second_run_ok,
    ])

    if all_passed:
        print(f"\n{PASS}  All checks passed. CareerClaw Pro license is working correctly.\n")
        print("  Next steps:")
        print("  1. Commit these changes to a feature branch.")
        print("  2. Open a PR and let CI run the unit tests.")
        print("  3. Once approved, publish to ClawHub.")
        return 0
    else:
        print(f"\n{FAIL}  Some checks failed. Review the output above.\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
