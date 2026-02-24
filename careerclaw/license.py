# careerclaw/license.py
#
# Handles CareerClaw Pro license validation via LemonSqueezy.
#
# Flow:
#   1. On first use: activate the key against LemonSqueezy API (consumes 1 activation slot).
#   2. Write a local cache file (.careerclaw/.license_cache) with key hash + timestamp.
#   3. On later runs: read cache. Re-validate against LemonSqueezy every 7 days.
#   4. If LemonSqueezy is unreachable: allow a 24h grace period before downgrading to free.
#
# The raw license key is NEVER written to disk — only a SHA-256 hash is cached.

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

# ── LemonSqueezy product identifiers ─────────────────────────────────────────

_LS_PRODUCT_ID = 847188
_LS_VARIANT_ID = 1334876
_LS_ACTIVATE_URL = "https://api.lemonsqueezy.com/v1/licenses/activate"
_LS_VALIDATE_URL = "https://api.lemonsqueezy.com/v1/licenses/validate"
_INSTANCE_NAME = "careerclaw-local"

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


def _write_cache(key: str, *, valid: bool, instance_id: Optional[str] = None) -> None:
    """Write (or overwrite) the cache file."""
    path = _cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "key_hash": _key_hash(key),
        "valid": valid,
        "validated_at": time.time(),
        "instance_id": instance_id or "",
    }
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except Exception:
        pass  # cache write failure never blocks a run


def _ls_post(url: str, params: dict) -> dict:
    """
    POST to a LemonSqueezy license endpoint.
    Raises urllib.error.URLError on network failure.
    Raises ValueError on non-200 status or invalid JSON.
    """
    body = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode()
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return json.loads(raw)
        except Exception:
            raise ValueError(f"LemonSqueezy returned HTTP {e.code}: {raw}") from e


def _activate(key: str) -> tuple[bool, Optional[str]]:
    """
    Activate the key. Returns (success, instance_id).
    instance_id is needed for future validate calls.
    """
    try:
        resp = _ls_post(_LS_ACTIVATE_URL, {
            "license_key": key,
            "instance_name": _INSTANCE_NAME,
        })
        activated = resp.get("activated", False)
        instance_id = (resp.get("instance") or {}).get("id")
        return bool(activated), instance_id
    except urllib.error.URLError:
        return False, None
    except ValueError:
        return False, None


def _validate_remote(key: str, instance_id: str) -> Optional[bool]:
    """
    Validate an already-activated key.
    Returns True/False, or None if the network call failed (caller applies grace period).
    """
    try:
        resp = _ls_post(_LS_VALIDATE_URL, {
            "license_key": key,
            "instance_id": instance_id,
        })
        return bool(resp.get("valid", False))
    except urllib.error.URLError:
        return None  # network failure — caller decides grace
    except ValueError:
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def pro_licensed(key: Optional[str] = None) -> bool:
    """
    Return True if the CareerClaw Pro license is valid.

    Decision tree:
      1. No key → free tier.
      2. Cache hit + same key + validated recently (< 7 days) → Pro.
      3. Cache hit + same key + stale → re-validate remotely.
         - Remote says valid → update cache → Pro.
         - Remote unreachable + last validated < 24h ago → grace → Pro.
         - Remote unreachable + last validated >= 24h ago → free + warning.
         - Remote says invalid → update cache (invalid) → free + warning.
      4. No cache (first use) → activate remotely.
         - Activation success → write cache → Pro.
         - Activation failure (network) → free + warning.
         - Activation failure (invalid key) → free + warning.
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

        # Cache is stale — re-validate remotely.
        instance_id = cache.get("instance_id", "")
        remote_result = _validate_remote(key, instance_id)

        if remote_result is True:
            _write_cache(key, valid=True, instance_id=instance_id)
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

        # Remote says invalid.
        _write_cache(key, valid=False, instance_id=instance_id)
        print(
            "[CareerClaw] Pro license is no longer valid. Running in free tier.",
            file=sys.stderr,
        )
        return False

    # No cache — first use. Attempt activation.
    activated, instance_id = _activate(key)

    if activated and instance_id:
        _write_cache(key, valid=True, instance_id=instance_id)
        return True

    if instance_id is None and not activated:
        # Could be a network failure or an invalid key.
        # We can't distinguish without a successful response, so fail safe.
        print(
            "[CareerClaw] Could not activate Pro license. "
            "Check your CAREERCLAW_PRO_KEY and internet connection. Running in free tier.",
            file=sys.stderr,
        )
        return False

    print(
        "[CareerClaw] Pro license activation failed. Running in free tier.",
        file=sys.stderr,
    )
    return False
