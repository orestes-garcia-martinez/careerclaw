#!/usr/bin/env python3
# scripts/smoke_test_license.py
#
# End-to-end smoke test for the CareerClaw Pro license system (Gumroad).
#
# Usage:
#   CAREERCLAW_PRO_KEY=<your-key> python scripts/smoke_test_license.py

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from careerclaw.license import pro_licensed, _cache_path, _key_hash

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"
_results: list[tuple[str, bool]] = []

def check(label: str, condition: bool) -> None:
    status = PASS if condition else FAIL
    print(f"  [{status}] {label}")
    _results.append((label, condition))

def main() -> int:
    key = os.environ.get("CAREERCLAW_PRO_KEY", "").strip()
    if not key:
        print("ERROR: CAREERCLAW_PRO_KEY is not set.")
        print("Usage: CAREERCLAW_PRO_KEY=<your-key> python scripts/smoke_test_license.py")
        return 1

    tmp_dir = tempfile.mkdtemp(prefix="careerclaw_smoke_")
    fake_careerclaw = Path(tmp_dir) / ".careerclaw"
    fake_careerclaw.mkdir()
    original_cwd = Path.cwd()
    os.chdir(tmp_dir)

    try:
        print("\n── Test 1: First verify (no cache) ───────────────────────────")
        result = pro_licensed(key)
        check("pro_licensed() returns True with valid key", result is True)

        cache_file = fake_careerclaw / ".license_cache"
        check("Cache file created", cache_file.exists())

        if cache_file.exists():
            cache = json.loads(cache_file.read_text())
            check("Cache contains key_hash", "key_hash" in cache)
            check("key_hash matches SHA-256", cache.get("key_hash") == _key_hash(key))
            check("Raw key NOT in cache", key not in cache_file.read_text())
            check("Cache valid=True", cache.get("valid") is True)

        print("\n── Test 2: Cache hit (no network) ────────────────────────────")
        check("pro_licensed() returns True from cache", pro_licensed(key) is True)

        print("\n── Test 3: No key → free tier ────────────────────────────────")
        check("pro_licensed(None) returns False", pro_licensed(None) is False)
        check("pro_licensed('') returns False", pro_licensed("") is False)

        print("\n── Test 4: Invalid key → free tier ───────────────────────────")
        if cache_file.exists():
            cache_file.unlink()
        check("Invalid key returns False",
              pro_licensed("INVALID-0000-0000-0000-000000000000") is False)

    finally:
        os.chdir(original_cwd)
        shutil.rmtree(tmp_dir, ignore_errors=True)

    passed = sum(1 for _, ok in _results if ok)
    failed = len(_results) - passed
    print(f"\n── Results: {passed}/{len(_results)} passed", end="")
    print(f"  ({failed} FAILED)" if failed else "  ✓")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
