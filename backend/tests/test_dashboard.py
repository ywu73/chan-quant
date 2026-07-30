from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from chan_quant.api.app import app
from chan_quant.domain.dashboard import StructuralTiming
from chan_quant.services.mock_dashboard import (
    build_mock_dashboard,
    line_spread_pct,
    relative_to_line,
)


def test_confirmed_display_formulas_match_reference_values() -> None:
    current_price = 108.18
    buy_line = 102.53
    sell_line = 129.54
    ma57 = 144.85

    assert relative_to_line(current_price, buy_line) == pytest.approx(0.0551, abs=0.0001)
    assert relative_to_line(current_price, sell_line) == pytest.approx(-0.1649, abs=0.0001)
    assert relative_to_line(current_price, ma57) == pytest.approx(-0.2532, abs=0.0001)
    assert line_spread_pct(buy_line, sell_line) == pytest.approx(-0.2085, abs=0.0001)


def test_mock_snapshot_accounting_and_signal_timing() -> None:
    snapshot = build_mock_dashboard()

    performance = snapshot.signal_performance
    assert performance.headline_total == 54
    assert (
        performance.buy.total_signals + performance.sell.total_signals + performance.excluded_total
        == 54
    )
    assert snapshot.is_mock is True
    assert snapshot.strategy.rule_status == "MOCK"

    for signal in snapshot.chart.signals:
        assert signal.timing.structure_at <= signal.timing.confirmed_at
        assert signal.timing.confirmed_at <= signal.timing.executable_at


def test_structural_timing_rejects_future_leak_order() -> None:
    now = datetime(2026, 7, 30, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        StructuralTiming(
            structure_at=now,
            confirmed_at=now - timedelta(days=1),
            executable_at=now + timedelta(days=1),
        )


def test_dashboard_endpoint_is_explicitly_mock() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/instruments/demo.sz/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_mock"] is True
    assert payload["instrument"]["symbol"] == "DEMO.SZ"
    assert payload["strategy"]["rule_status"] == "MOCK"
