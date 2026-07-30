from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from chan_quant.api.app import app
from chan_quant.domain.dashboard import StructuralTiming
from chan_quant.services.dashboard_builder import (
    line_spread_pct,
    relative_to_line,
)
from chan_quant.services.demo_market import build_demo_bars
from chan_quant.services.mock_dashboard import build_mock_dashboard


def _write_demo_csv(path: Path, count: int) -> None:
    rows = ["trade_date,open,high,low,close,volume,amount"]
    for bar in build_demo_bars(count=count):
        rows.append(
            f"{bar.date.isoformat()},{bar.open},{bar.high},{bar.low},"
            f"{bar.close},{bar.volume},"
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def test_confirmed_display_formulas_match_reference_values() -> None:
    current_price = 108.18
    buy_line = 102.53
    sell_line = 129.54
    ma57 = 144.85

    assert relative_to_line(current_price, buy_line) == pytest.approx(0.0551, abs=0.0001)
    assert relative_to_line(current_price, sell_line) == pytest.approx(-0.1649, abs=0.0001)
    assert relative_to_line(current_price, ma57) == pytest.approx(-0.2532, abs=0.0001)
    assert line_spread_pct(buy_line, sell_line) == pytest.approx(-0.2085, abs=0.0001)


def test_calculated_demo_snapshot_accounting_and_signal_timing() -> None:
    snapshot = build_mock_dashboard()

    performance = snapshot.signal_performance
    assert (
        performance.buy.total_signals + performance.sell.total_signals + performance.excluded_total
        == performance.headline_total
    )
    assert snapshot.is_mock is True
    assert snapshot.strategy.rule_status == "DRAFT"
    assert snapshot.strategy.version == "independent-v0.1.0"
    assert all(not signal.id.startswith("MOCK-") for signal in snapshot.chart.signals)

    for signal in snapshot.chart.signals:
        assert signal.timing.structure_at <= signal.timing.confirmed_at
        if signal.timing.executable_at is not None:
            assert signal.timing.confirmed_at <= signal.timing.executable_at


def test_structural_timing_rejects_future_leak_order() -> None:
    now = datetime(2026, 7, 30, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        StructuralTiming(
            structure_at=now,
            confirmed_at=now - timedelta(days=1),
            executable_at=now + timedelta(days=1),
        )


def test_dashboard_endpoint_is_explicitly_synthetic_draft() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/instruments/demo.sz/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_mock"] is True
    assert payload["instrument"]["symbol"] == "DEMO.SZ"
    assert payload["instrument"]["data_source"] == "deterministic-synthetic"
    assert payload["strategy"]["rule_status"] == "DRAFT"


def test_dashboard_endpoint_uses_explicit_csv_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "bars.csv"
    _write_demo_csv(source, count=120)
    monkeypatch.setenv("CHAN_QUANT_CSV_PATH", str(source))
    monkeypatch.setenv("CHAN_QUANT_ADJUSTMENT", "qfq")
    monkeypatch.setenv("CHAN_QUANT_INSTRUMENT_NAME", "CSV 测试标的")

    response = TestClient(app).get("/api/v1/instruments/000001.sz/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_mock"] is False
    assert payload["instrument"]["symbol"] == "000001.SZ"
    assert payload["instrument"]["name"] == "CSV 测试标的"
    assert payload["instrument"]["data_source"] == "csv"
    assert payload["instrument"]["adjustment"] == "qfq"
    assert payload["strategy"]["rule_status"] == "DRAFT"


def test_dashboard_endpoint_rejects_insufficient_csv_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "short.csv"
    _write_demo_csv(source, count=91)
    monkeypatch.setenv("CHAN_QUANT_CSV_PATH", str(source))

    response = TestClient(app).get("/api/v1/instruments/000001.sz/dashboard")

    assert response.status_code == 422
    assert response.json()["detail"] == "expected at least 92 bars, got 91"
