# tests/unit/test_license.py
#
# Tests for careerclaw/license.py
#
# All tests mock Gumroad network calls and the cache file — no real
# HTTP requests are made, no disk state is left behind.

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from careerclaw import license as lic


# ── Helpers ───────────────────────────────────────────────────────────────────

FAKE_KEY = "TEST-1234-ABCD-5678"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    """Redirect cache writes/reads to a temp directory for every test."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".careerclaw").mkdir()
    return tmp_path


# ── No key → free tier ────────────────────────────────────────────────────────

def test_no_key_returns_false():
    assert lic.pro_licensed(None) is False


def test_empty_string_returns_false():
    assert lic.pro_licensed("") is False


# ── First use: verify ─────────────────────────────────────────────────────────

def test_first_use_valid_key_returns_true():
    with patch.object(lic, "_gr_verify", return_value=True):
        result = lic.pro_licensed(FAKE_KEY)
    assert result is True


def test_first_use_valid_key_writes_cache():
    with patch.object(lic, "_gr_verify", return_value=True):
        lic.pro_licensed(FAKE_KEY)
    cache = json.loads(lic._cache_path().read_text())
    assert cache["valid"] is True
    assert cache["key_hash"] == lic._key_hash(FAKE_KEY)
    assert "validated_at" in cache
    # Raw key must never be stored
    assert FAKE_KEY not in lic._cache_path().read_text()


def test_first_use_invalid_key_returns_false(capsys):
    with patch.object(lic, "_gr_verify", return_value=False):
        result = lic.pro_licensed(FAKE_KEY)
    assert result is False
    assert "free tier" in capsys.readouterr().err


def test_first_use_network_failure_returns_false(capsys):
    with patch.object(lic, "_gr_verify", return_value=None):
        result = lic.pro_licensed(FAKE_KEY)
    assert result is False
    assert "free tier" in capsys.readouterr().err


def test_first_use_increments_usage():
    """First use must call _gr_verify with increment_uses=True."""
    with patch.object(lic, "_gr_verify", return_value=True) as mock_verify:
        lic.pro_licensed(FAKE_KEY)
    mock_verify.assert_called_once_with(FAKE_KEY, increment_uses=True)


# ── Cache hit: fresh ──────────────────────────────────────────────────────────

def test_fresh_cache_valid_returns_true_without_network():
    lic._write_cache(FAKE_KEY, valid=True)

    with patch.object(lic, "_gr_verify") as mock_verify:
        result = lic.pro_licensed(FAKE_KEY)

    mock_verify.assert_not_called()
    assert result is True


def test_fresh_cache_invalid_returns_false_without_network():
    lic._write_cache(FAKE_KEY, valid=False)

    with patch.object(lic, "_gr_verify") as mock_verify:
        result = lic.pro_licensed(FAKE_KEY)

    mock_verify.assert_not_called()
    assert result is False


# ── Cache hit: stale (> 7 days) ───────────────────────────────────────────────

def _write_stale_cache(key: str, *, valid: bool, age_seconds: float):
    """Write a cache entry with a backdated validated_at timestamp."""
    path = lic._cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "key_hash": lic._key_hash(key),
        "valid": valid,
        "validated_at": time.time() - age_seconds,
    }
    path.write_text(json.dumps(payload))


def test_stale_cache_remote_valid_refreshes_cache():
    stale_age = lic._REVALIDATE_INTERVAL_SECONDS + 100
    _write_stale_cache(FAKE_KEY, valid=True, age_seconds=stale_age)

    with patch.object(lic, "_gr_verify", return_value=True):
        result = lic.pro_licensed(FAKE_KEY)

    assert result is True
    cache = json.loads(lic._cache_path().read_text())
    age = time.time() - cache["validated_at"]
    assert age < 5  # refreshed within last 5 seconds


def test_stale_cache_revalidation_does_not_increment_usage():
    """Revalidation must call _gr_verify with increment_uses=False."""
    stale_age = lic._REVALIDATE_INTERVAL_SECONDS + 100
    _write_stale_cache(FAKE_KEY, valid=True, age_seconds=stale_age)

    with patch.object(lic, "_gr_verify", return_value=True) as mock_verify:
        lic.pro_licensed(FAKE_KEY)

    mock_verify.assert_called_once_with(FAKE_KEY, increment_uses=False)


def test_stale_cache_remote_invalid_returns_false(capsys):
    stale_age = lic._REVALIDATE_INTERVAL_SECONDS + 100
    _write_stale_cache(FAKE_KEY, valid=True, age_seconds=stale_age)

    with patch.object(lic, "_gr_verify", return_value=False):
        result = lic.pro_licensed(FAKE_KEY)

    assert result is False
    assert "free tier" in capsys.readouterr().err


# ── Grace period ──────────────────────────────────────────────────────────────

def test_stale_cache_network_failure_within_grace_returns_true():
    stale_age = lic._REVALIDATE_INTERVAL_SECONDS + 3600  # 7 days + 1 hour
    _write_stale_cache(FAKE_KEY, valid=True, age_seconds=stale_age)

    with patch.object(lic, "_gr_verify", return_value=None):
        result = lic.pro_licensed(FAKE_KEY)

    assert result is True


def test_stale_cache_network_failure_beyond_grace_returns_false(capsys):
    stale_age = lic._REVALIDATE_INTERVAL_SECONDS + lic._GRACE_PERIOD_SECONDS + 3600
    _write_stale_cache(FAKE_KEY, valid=True, age_seconds=stale_age)

    with patch.object(lic, "_gr_verify", return_value=None):
        result = lic.pro_licensed(FAKE_KEY)

    assert result is False
    assert "grace period expired" in capsys.readouterr().err


# ── Key hash isolation ────────────────────────────────────────────────────────

def test_different_key_ignores_existing_cache():
    """Cache for key A must not unlock Pro for key B."""
    lic._write_cache(FAKE_KEY, valid=True)

    different_key = "DIFFERENT-KEY-9999"
    with patch.object(lic, "_gr_verify", return_value=False):
        result = lic.pro_licensed(different_key)

    assert result is False


# ── config.pro_licensed() integration ────────────────────────────────────────

def test_config_pro_licensed_no_env_returns_false(monkeypatch):
    monkeypatch.delenv("CAREERCLAW_PRO_KEY", raising=False)
    import importlib
    from careerclaw import config
    importlib.reload(config)
    assert config.pro_licensed() is False


def test_config_pro_licensed_with_valid_key(monkeypatch):
    monkeypatch.setenv("CAREERCLAW_PRO_KEY", FAKE_KEY)
    import importlib
    from careerclaw import config
    importlib.reload(config)

    with patch.object(lic, "_gr_verify", return_value=True):
        result = config.pro_licensed()

    assert result is True
