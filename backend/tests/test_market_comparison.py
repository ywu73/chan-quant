from datetime import date
from threading import Barrier

import pytest
from fastapi.testclient import TestClient

from chan_quant.api.app import app
from chan_quant.data.sina_source import SinaUpstreamError
from chan_quant.domain.instrument import InstrumentIdentity
from chan_quant.domain.market import MarketBar
from chan_quant.services.market_comparison import (
    ComparisonInput,
    ComparisonLoadError,
    build_market_comparison,
)


def _bar(day: int, close: float) -> MarketBar:
    return MarketBar(
        date=date(2026, 1, day),
        open=close,
        high=close,
        low=close,
        close=close,
        volume=1_000,
    )


def _input(symbol: str, name: str, bars: list[MarketBar]) -> ComparisonInput:
    return ComparisonInput(
        instrument=InstrumentIdentity(
            symbol=symbol,
            name=name,
            exchange=symbol.rsplit(".", 1)[1],
            asset_type="UNKNOWN",
            price_precision=2,
        ),
        bars=bars,
        data_source="test-history",
        adjustment="qfq",
        is_mock=False,
        warnings=[],
    )


def test_comparison_aligns_union_dates_without_filling_and_calculates_metrics() -> None:
    inputs = {
        "000001.SZ": _input(
            "000001.SZ",
            "甲标的",
            [_bar(1, 100), _bar(2, 110), _bar(3, 88)],
        ),
        "600000.SH": _input(
            "600000.SH",
            "乙标的",
            [_bar(1, 50), _bar(3, 55)],
        ),
    }

    result = build_market_comparison(
        ["000001.SZ", "600000.SH"],
        inputs.__getitem__,
    )

    assert result.status == "COMPLETE"
    assert result.requested == ["000001.SZ", "600000.SH"]
    assert result.succeeded == 2
    assert result.failed == 0
    assert result.common_from == date(2026, 1, 1)
    assert result.common_to == date(2026, 1, 3)
    assert result.dates == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]

    first, second = result.series
    assert first.baseline_price == 100
    assert first.latest_close == 88
    assert first.previous_trading_day_return == pytest.approx(0.1)
    assert first.values == pytest.approx([0.0, 0.1, -0.12])
    assert first.cumulative_return == pytest.approx(-0.12)
    assert first.max_drawdown == pytest.approx(-0.2)
    assert first.max_drawdown_peak_at == date(2026, 1, 2)
    assert first.max_drawdown_trough_at == date(2026, 1, 3)
    assert first.coverage_ratio == 1.0

    assert second.values[0] == 0.0
    assert second.baseline_price == 50
    assert second.latest_close == 55
    assert second.previous_trading_day_return is None
    assert second.values[1] is None
    assert second.values[2] == pytest.approx(0.1)
    assert second.cumulative_return == pytest.approx(0.1)
    assert second.max_drawdown == 0.0
    assert second.max_drawdown_peak_at is None
    assert second.max_drawdown_trough_at is None
    assert second.coverage_ratio == pytest.approx(2 / 3)


def test_comparison_keeps_successful_series_when_one_symbol_fails() -> None:
    inputs = {
        "000001.SZ": _input(
            "000001.SZ",
            "甲标的",
            [_bar(1, 100), _bar(2, 101)],
        ),
        "600000.SH": _input(
            "600000.SH",
            "乙标的",
            [_bar(1, 50), _bar(2, 49)],
        ),
    }

    def load(symbol: str) -> ComparisonInput:
        if symbol == "300001.SZ":
            raise ComparisonLoadError("UPSTREAM_UNAVAILABLE", "测试上游不可用")
        return inputs[symbol]

    result = build_market_comparison(
        ["000001.SZ", "300001.SZ", "600000.SH"],
        load,
    )

    assert result.status == "PARTIAL"
    assert result.succeeded == 2
    assert result.failed == 1
    assert [series.instrument.symbol for series in result.series] == [
        "000001.SZ",
        "600000.SH",
    ]
    assert [failure.model_dump() for failure in result.failures] == [
        {
            "symbol": "300001.SZ",
            "code": "UPSTREAM_UNAVAILABLE",
            "message": "测试上游不可用",
        }
    ]


def test_comparison_loads_in_parallel_but_keeps_requested_order() -> None:
    symbols = ["000001.SZ", "300001.SZ", "600000.SH", "688001.SH"]
    barrier = Barrier(len(symbols), timeout=2)

    def load(symbol: str) -> ComparisonInput:
        barrier.wait()
        if symbol == "300001.SZ":
            raise ComparisonLoadError("UPSTREAM_UNAVAILABLE", "test upstream unavailable")
        return _input(symbol, symbol, [_bar(1, 100), _bar(2, 101)])

    result = build_market_comparison(symbols, load, max_workers=4)

    assert result.status == "PARTIAL"
    assert [series.instrument.symbol for series in result.series] == [
        "000001.SZ",
        "600000.SH",
        "688001.SH",
    ]
    assert [failure.symbol for failure in result.failures] == ["300001.SZ"]


def test_comparison_rejects_non_positive_worker_limit() -> None:
    with pytest.raises(ValueError, match="comparison max_workers must be positive"):
        build_market_comparison([], lambda symbol: _input(symbol, symbol, []), max_workers=0)


def test_comparison_applies_requested_range_before_normalizing() -> None:
    source = _input(
        "000001.SZ",
        "甲标的",
        [_bar(1, 80), _bar(2, 100), _bar(3, 125)],
    )

    result = build_market_comparison(
        ["000001.SZ"],
        lambda symbol: source,
        start=date(2026, 1, 2),
        end=date(2026, 1, 3),
    )

    assert result.series[0].baseline_at == date(2026, 1, 2)
    assert result.series[0].baseline_price == 100
    assert result.series[0].latest_close == 125
    assert result.series[0].previous_trading_day_return is None
    assert result.series[0].values == pytest.approx([0.0, 0.25])
    assert result.series[0].cumulative_return == pytest.approx(0.25)


def test_market_comparison_endpoint_returns_partial_sina_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "sina")

    def fetch_bars(symbol: str, *, datalen: int) -> list[MarketBar]:
        assert datalen == 2_000
        if symbol == "300001.SZ":
            raise SinaUpstreamError("test upstream unavailable")
        return (
            [_bar(1, 100), _bar(2, 110), _bar(3, 88)]
            if symbol == "000001.SZ"
            else [_bar(1, 50), _bar(3, 55)]
        )

    def fetch_instrument(symbol: str) -> InstrumentIdentity:
        return InstrumentIdentity(
            symbol=symbol,
            name={"000001.SZ": "甲标的", "600000.SH": "乙标的"}[symbol],
            exchange=symbol.rsplit(".", 1)[1],
            asset_type="UNKNOWN",
            price_precision=2,
        )

    monkeypatch.setattr("chan_quant.api.app.fetch_sina_kline_bars", fetch_bars)
    monkeypatch.setattr("chan_quant.api.app.fetch_sina_instrument", fetch_instrument)

    response = TestClient(app).get(
        "/api/v1/market-comparison",
        params=[
            ("symbols", "000001.sz"),
            ("symbols", "300001.SZ"),
            ("symbols", "600000.SH"),
            ("start", "2026-01-01"),
            ("end", "2026-01-03"),
        ],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "PARTIAL"
    assert payload["requested"] == ["000001.SZ", "300001.SZ", "600000.SH"]
    assert payload["dates"] == ["2026-01-01", "2026-01-02", "2026-01-03"]
    assert payload["series"][0]["baseline_price"] == 100
    assert payload["series"][0]["latest_close"] == 88
    assert payload["series"][0]["previous_trading_day_return"] == pytest.approx(0.1)
    assert payload["series"][1]["values"] == [0.0, None, pytest.approx(0.1)]
    assert payload["failures"] == [
        {
            "symbol": "300001.SZ",
            "code": "UPSTREAM_UNAVAILABLE",
            "message": "test upstream unavailable",
        }
    ]
    assert payload["series"][0]["warnings"][0]["code"] == ("DATA_SOURCE_ADJUSTMENT_UNCONTRACTED")


def test_market_comparison_endpoint_accepts_eight_symbols(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "sina")
    symbols = [f"{code:06d}.SZ" for code in range(1, 9)]

    monkeypatch.setattr(
        "chan_quant.api.app.fetch_sina_kline_bars",
        lambda symbol, *, datalen: [_bar(1, 100), _bar(2, 101)],
    )
    monkeypatch.setattr(
        "chan_quant.api.app.fetch_sina_instrument",
        lambda symbol: InstrumentIdentity(
            symbol=symbol,
            name=symbol,
            exchange="SZ",
            asset_type="UNKNOWN",
            price_precision=2,
        ),
    )

    response = TestClient(app).get(
        "/api/v1/market-comparison",
        params=[("symbols", symbol) for symbol in symbols],
    )

    assert response.status_code == 200
    assert response.json()["requested"] == symbols


@pytest.mark.parametrize(
    ("params", "message"),
    [
        ([("symbols", "000001.SZ")], "comparison requires 2 to 8 symbols"),
        (
            [("symbols", f"{code:06d}.SZ") for code in range(1, 10)],
            "comparison requires 2 to 8 symbols",
        ),
        (
            [("symbols", "000001.SZ"), ("symbols", "000001.sz")],
            "comparison symbols must be distinct",
        ),
        (
            [("symbols", "000001.SZ"), ("symbols", "INVALID")],
            "Sina sources support only NNNNNN.SZ or NNNNNN.SH",
        ),
    ],
)
def test_market_comparison_endpoint_rejects_invalid_symbol_sets(
    monkeypatch: pytest.MonkeyPatch,
    params: list[tuple[str, str]],
    message: str,
) -> None:
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "sina")

    response = TestClient(app).get("/api/v1/market-comparison", params=params)

    assert response.status_code == 422
    assert response.json()["detail"] == message


def test_market_comparison_endpoint_rejects_single_file_data_modes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "snapshot")

    response = TestClient(app).get(
        "/api/v1/market-comparison",
        params=[("symbols", "000001.SZ"), ("symbols", "600000.SH")],
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "multi-symbol comparison currently requires CHAN_QUANT_DATA_SOURCE=sina; "
        "single CSV and snapshot packages cannot represent multiple instruments"
    )


def test_market_comparison_endpoint_rejects_reversed_date_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "sina")

    response = TestClient(app).get(
        "/api/v1/market-comparison",
        params=[
            ("symbols", "000001.SZ"),
            ("symbols", "600000.SH"),
            ("start", "2026-02-01"),
            ("end", "2026-01-01"),
        ],
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "comparison start date must not be after end date"
