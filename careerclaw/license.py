# careerclaw/license.py
#
# Handles CareerClaw Pro license validation via Gumroad.
#
# Flow:
#   1. On first use: verify the key against Gumroad API.
#   2. Write a local cache file (.careerclaw/.license_cache) with key hash + timestamp.
#   3. On later runs: read cache. Re-validate against Gumroad every 7 days.
#   4. If Gumroad is unreachable: allow a 24h grace period before downgrading to free.
#
# The raw license key is NEVER written to disk — only a SHA-256 hash is cached.
#
# Note: Gumroad uses a single /verify endpoint for both first use and revalidation.
#       We set increment_uses_count=false on revalidation to avoid burning usage quota.

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

# ── Gumroad product identifier ────────────────────────────────────────────────
# Found in your Gumroad product → Content page → License key module → product_id
# Required for products created after Jan 9 2023.

_GR_PRODUCT_ID = "RFgXMtGajXKJfDvpZOXtfA=="
_GR_VERIFY_URL = "https://api.gumroad.com/v2/licenses/verify"

# ── Cache settings ────────────────────────────────────────────────────────────

_REVALIDATE_INTERVAL_SECONDS = 7 * 24 * 3600   # 7 days
_GRACE_PERIOD_SECONDS = 24 * 3600              # 24 hours
_CACHE_FILENAME = ".license_cache"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _key_hash(key: str) -> str:
    """One-way hash of the raw key — safe to store on disk."""
    return hashlib.sha256(key.encode()).hexdigest()


def _cache_path() -> Path:
    return Path(".careerclaw") / _CACHE_FILENAME


def _read_cache(key: str) -> Optional[dict]:
    """
    Read the cache file. Returns the dict only if it belongs to the current key.
    Returns None if the file is missing, unreadable, or belongs to a different key.
    """
    path = _cache_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("key_hash") != _key_hash(key):
            return None
        return data
    except Exception:
        return None


def _write_cache(key: str, *, valid: bool) -> None:
    """Write (or overwrite) the cache file."""
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "key_hash": _key_hash(key),
        "valid": valid,
        "validated_at": time.time(),
    }
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass  # cache write failure never blocks a run


def _gr_verify(key: str, *, increment_uses: bool = True) -> Optional[bool]:
    """
    POST to Gumroad's license verify endpoint.
    Returns True if valid, False if invalid/refunded, None on network failure.
    """
    params = urllib.parse.urlencode({
        "product_id": _GR_PRODUCT_ID,
        "license_key": key,
        "increment_uses_count": "true" if increment_uses else "false",
    }).encode()

    req = urllib.request.Request(
        _GR_VERIFY_URL,
        data=params,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if not data.get("success"):
                return False
            purchase = data.get("purchase") or {}
            # Treat refunded or chargebacked purchases as invalid
            if purchase.get("refunded") or purchase.get("chargebacked"):
                return False
            return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False  # key does not exist
        return None       # other HTTP error — treat as network failure
    except urllib.error.URLError:
        return None       # network failure — caller applies grace period


# ── Public API ────────────────────────────────────────────────────────────────

def pro_licensed(key: Optional[str] = None) -> bool:
    """
    Return True if the CareerClaw Pro license is valid.

    Decision tree:
      1. No key → free tier.
      2. Cache hit + same key + validated recently (< 7 days) → Pro.
      3. Cache hit + same key + stale → re-validate remotely (no usage increment).
         - Remote says valid → update cache → Pro.
         - Remote unreachable + within grace period → Pro (grace).
         - Remote unreachable + grace expired → free + warning.
         - Remote says invalid → update cache (invalid) → free + warning.
      4. No cache (first use) → verify remotely (increments usage once).
         - Valid → write cache → Pro.
         - Invalid or network failure → free + warning.
    """
    if not key:
        return False

    cache = _read_cache(key)
    now = time.time()

    if cache is not None:
        validated_at = cache.get("validated_at", 0)
        age = now - validated_at

        # Cache is fresh — trust it.
        if age < _REVALIDATE_INTERVAL_SECONDS:
            return bool(cache.get("valid", False))

        # Cache is stale — re-validate without incrementing uses.
        remote_result = _gr_verify(key, increment_uses=False)

        if remote_result is True:
            _write_cache(key, valid=True)
            return True

        if remote_result is None:
            # Network failure — apply grace period.
            if age < _REVALIDATE_INTERVAL_SECONDS + _GRACE_PERIOD_SECONDS:
                return bool(cache.get("valid", False))
            else:
                print(
                    "[CareerClaw] Could not reach license server and grace period expired. "
                    "Running in free tier. Check your internet connection.",
                    file=sys.stderr,
                )
                return False

        # Remote says invalid (refunded, chargebacked, or bad key).
        _write_cache(key, valid=False)
        print(
            "[CareerClaw] Pro license is no longer valid. Running in free tier.",
            file=sys.stderr,
        )
        return False

    # No cache — first use. Verify and increment usage count.
    remote_result = _gr_verify(key, increment_uses=True)

    if remote_result is True:
        _write_cache(key, valid=True)
        return True

    if remote_result is None:
        print(
            "[CareerClaw] Could not reach license server. "
            "Check your CAREERCLAW_PRO_KEY and internet connection. Running in free tier.",
            file=sys.stderr,
        )
        return False

    print(
        "[CareerClaw] Pro license key is invalid or has been refunded. Running in free tier.",
        file=sys.stderr,
    )
    return False
