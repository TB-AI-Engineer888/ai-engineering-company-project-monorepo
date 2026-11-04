from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "services"))

from ttl_cache import TtlCache


def test_value_expires() -> None:
    cache = TtlCache()
    cache.set("inventory:products", [{"sku": "HCR-PPE-001"}], ttl_seconds=0.05)
    assert cache.get("inventory:products") == [{"sku": "HCR-PPE-001"}]
    time.sleep(0.06)
    assert cache.get("inventory:products") is None


def test_prefix_invalidation_clears_only_matching_keys() -> None:
    cache = TtlCache()
    cache.set("inventory:products", [1], ttl_seconds=30)
    cache.set("inventory:orders", [2], ttl_seconds=30)
    cache.set("profiles:me", {"name": "kept"}, ttl_seconds=30)
    assert cache.invalidate_prefix("inventory:") == 2
    assert cache.get("inventory:products") is None
    assert cache.get("inventory:orders") is None
    assert cache.get("profiles:me") == {"name": "kept"}


def test_zero_ttl_is_rejected() -> None:
    cache = TtlCache()
    try:
        cache.set("inventory:products", [], ttl_seconds=0)
    except ValueError as exc:
        assert "greater than zero" in str(exc)
    else:
        raise AssertionError("a TTL of zero must be rejected")
