from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from chan_quant.api.app import app
from chan_quant.data.sina_source import SinaUpstreamError
from chan_quant.domain.dashboard import StructuralTiming
from chan_quant.domain.instrument import InstrumentIdentity
from chan_quant.domain.strategy import TrendState
from chan_quant.services.dashboard_builder import (
    _regime,
    _trend_tone,
    line_spread_pct,
    relative_to_line,
)
from chan_quant.services.demo_market import build_demo_bars
from chan_quant.services.mock_dashboard import build_mock_dashboard


def _write_demo_csv(path: Path, count: int) -> None:
    rows = ["trade_date,open,high,low,close,volume,amount"]
    for bar in build_demo_bars(count=count):
        rows.append(
            f"{bar.date.isoformat()},{bar.open},{bar.high},{bar.low},{bar.close},{bar.volume},"
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


def test_dashboard_exposes_semantic_market_direction_tones() -> None:
    assert _trend_tone(TrendState.BULLISH) == "bullish"
    assert _trend_tone(TrendState.BEARISH) == "bearish"
    assert _trend_tone(TrendState.NEUTRAL) == "neutral"
    assert _regime(TrendState.BULLISH, TrendState.BULLISH) == ("双多", "bullish")
    assert _regime(TrendState.BEARISH, TrendState.BEARISH) == ("双空", "bearish")


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


def test_dashboard_endpoint_is_explicitly_synthetic_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "synthetic")
    monkeypatch.delenv("CHAN_QUANT_CSV_PATH", raising=False)
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
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "csv")
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
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "csv")
    monkeypatch.setenv("CHAN_QUANT_CSV_PATH", str(source))

    response = TestClient(app).get("/api/v1/instruments/000001.sz/dashboard")

    assert response.status_code == 422
    assert response.json()["detail"] == "expected at least 92 bars, got 91"


def test_dashboard_endpoint_uses_sina_source_with_observed_adjustment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "sina")
    monkeypatch.setattr(
        "chan_quant.api.app.fetch_sina_kline_bars",
        lambda symbol, *, datalen: build_demo_bars(count=120),
    )
    monkeypatch.setattr(
        "chan_quant.api.app.fetch_sina_instrument",
        lambda symbol: InstrumentIdentity(
            symbol="000001.SZ",
            name="平安银行",
            exchange="SZ",
            asset_type="UNKNOWN",
            price_precision=2,
        ),
    )

    response = TestClient(app).get("/api/v1/instruments/000001.sz/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_mock"] is False
    assert payload["instrument"]["symbol"] == "000001.SZ"
    assert payload["instrument"]["name"] == "平安银行"
    assert payload["instrument"]["data_source"] == "sina-undocumented-kline"
    assert payload["instrument"]["adjustment"] == "unadjusted-observed"
    assert payload["instrument"]["asset_type"] == "UNKNOWN"
    assert payload["instrument"]["price_precision"] == 2
    assert payload["recommendation"]["warnings"] == [
        {
            "type": "DATA_SOURCE_ADJUSTMENT_UNCONTRACTED",
            "severity": "WARNING",
            "message": (
                "三只股票样本的除权窗口观测与不复权原始行情一致，但新浪没有提供"
                "固定口径合同；除权除息仍可能制造机械结构和事件信号。"
            ),
        }
    ]


def test_dashboard_endpoint_uses_etf_metadata_precision_and_risk_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "sina")
    monkeypatch.setattr(
        "chan_quant.api.app.fetch_sina_kline_bars",
        lambda symbol, *, datalen: build_demo_bars(count=120),
    )
    monkeypatch.setattr(
        "chan_quant.api.app.fetch_sina_instrument",
        lambda symbol: InstrumentIdentity(
            symbol="513100.SH",
            name="纳指ETF国泰",
            exchange="SH",
            asset_type="ETF",
            price_precision=3,
        ),
    )

    response = TestClient(app).get("/api/v1/instruments/513100.sh/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["instrument"]["symbol"] == "513100.SH"
    assert payload["instrument"]["name"] == "纳指ETF国泰"
    assert payload["instrument"]["asset_type"] == "ETF"
    assert payload["instrument"]["price_precision"] == 3
    assert payload["instrument"]["adjustment"] == "unspecified"
    assert payload["metrics"][0]["value"].count(".") == 1
    assert len(payload["metrics"][0]["value"].split(".")[1]) == 3
    assert payload["recommendation"]["warnings"] == [
        {
            "type": "ETF_ADJUSTMENT_UNVERIFIED",
            "severity": "WARNING",
            "message": (
                "该 ETF 的复权、分红与份额折算口径尚未完成审计；"
                "原始序列中的机械跳变会直接进入指标、结构、信号和事件研究。"
            ),
        }
    ]
    assert "ETF 日 K" in payload["recommendation"]["summary"]


def test_sina_dashboard_falls_back_to_symbol_when_metadata_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "sina")
    monkeypatch.setenv("CHAN_QUANT_INSTRUMENT_NAME", "错误的全局名称")
    monkeypatch.setattr(
        "chan_quant.api.app.fetch_sina_kline_bars",
        lambda symbol, *, datalen: build_demo_bars(count=120),
    )

    def fail_metadata(symbol: str) -> str:
        del symbol
        raise SinaUpstreamError("metadata unavailable")

    monkeypatch.setattr("chan_quant.api.app.fetch_sina_instrument", fail_metadata)

    response = TestClient(app).get("/api/v1/instruments/600519.sh/dashboard")

    assert response.status_code == 200
    assert response.json()["instrument"]["name"] == "600519.SH"
    assert response.json()["instrument"]["adjustment"] == "unspecified"
    assert response.json()["recommendation"]["warnings"][0]["type"] == (
        "INSTRUMENT_METADATA_UNAVAILABLE"
    )


def test_dashboard_endpoint_maps_sina_upstream_failure_to_502(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "sina")

    def fail_fetch(symbol: str, *, datalen: int):
        del symbol, datalen
        raise SinaUpstreamError("Sina K-line request returned HTTP 403")

    monkeypatch.setattr("chan_quant.api.app.fetch_sina_kline_bars", fail_fetch)

    response = TestClient(app).get("/api/v1/instruments/000001.sz/dashboard")

    assert response.status_code == 502
    assert response.json()["detail"] == "Sina K-line request returned HTTP 403"
