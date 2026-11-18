"""Unit tests for the clinic supply KPI tasks.

Fixtures are in-memory telemetry events. No database and no external API.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.pipelines.pipeline import (
    critical_stockout_frequency,
    expiry_risk_count,
    supply_consumption_volume,
    supply_cost_per_clinic,
)


def _run(task, events):
    function = getattr(task, "fn", task)
    return function(events)


def _event(event_id: str, event_type: str, clinic_id: object, country: object, **properties: object) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "clinic_id": clinic_id,
        "country": country,
        **properties,
    }


def test_supply_cost_per_clinic_matches_the_briefing_sum() -> None:
    events = [
        _event("e1", "inbound_order_created", "1", "US", total_cost=10),
        _event("e2", "inbound_order_created", "1", "US", total_cost=15.5),
        _event("e3", "inbound_order_created", "10", "UK", total_cost=5),
        _event("e4", "outbound_order_created", "1", "US"),
    ]
    costs = _run(supply_cost_per_clinic, events)
    assert costs["1"] == 25.5
    assert costs["10"] == 5.0
    assert costs["2"] == 0.0


def test_supply_consumption_volume_counts_outbound_events() -> None:
    events = [
        _event("e1", "outbound_order_created", "4", "US"),
        _event("e2", "outbound_order_created", "4", "US"),
        _event("e3", "inbound_order_created", "4", "US", total_cost=8),
    ]
    counts = _run(supply_consumption_volume, events)
    assert counts["4"] == 2
    assert counts["5"] == 0


def test_critical_stockout_frequency_counts_threshold_events() -> None:
    events = [
        _event("e1", "stock_threshold_triggered", "12", "UK"),
        _event("e2", "stock_threshold_triggered", "12", "UK"),
        _event("e3", "supply_expiry_flagged", "12", "UK"),
    ]
    counts = _run(critical_stockout_frequency, events)
    assert counts["12"] == 2
    assert counts["11"] == 0


def test_expiry_risk_count_counts_flagged_batches() -> None:
    events = [
        _event("e1", "supply_expiry_flagged", "7", "US"),
        _event("e2", "stock_threshold_triggered", "7", "US"),
    ]
    counts = _run(expiry_risk_count, events)
    assert counts["7"] == 1


def test_supply_cost_ignores_null_and_malformed_cost() -> None:
    events = [
        _event("e1", "inbound_order_created", "1", "US", total_cost=None),
        _event("e2", "inbound_order_created", "1", "US", total_cost="not-a-cost"),
        _event("e3", "inbound_order_created", None, "US", total_cost=40),
        _event("e4", "inbound_order_created", "1", "UK", total_cost=40),
        _event("e5", "inbound_order_created", "1", "US", total_cost=4),
    ]
    costs = _run(supply_cost_per_clinic, events)
    assert costs["1"] == 4.0
