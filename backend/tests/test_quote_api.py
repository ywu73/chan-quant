from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from chan_quant.api.app import app
from chan_quant.data.sina_quote_source import SinaQuoteUnavailableError
from chan_quant.data.sina_source import SinaDataError, SinaUpstreamError
from chan_quant.domain.quote import QuoteBatch, QuoteFailure, QuoteSnapshot

SHANGHAI_TZ = timezone(timedelta(hours=8))


def _snapshot() -> QuoteSnapshot:
    return QuoteSnapshot(
        symbol="000001.SZ",
        name="平安银行",
        last_price=11.62,
        previous_close=11.48,
        change=0.14,
        change_percent=0.012195,
        open=11.48,
        high=11.67,
        low=11.42,
        volume=63_210_000,
        quote_at=datetime(2026, 7, 31, 14, 35, 6, tzinfo=SHANGHAI_TZ),
        received_at=datetime(2026, 7, 31, 14, 35, 7, tzinfo=SHANGHAI_TZ),
        status="LIVE",
        is_stale=False,
    )


def _batch() -> QuoteBatch:
    return QuoteBatch(
        status="PARTIAL",
        requested=["000001.SZ", "600000.SH"],
        succeeded=1,
        failed=1,
        quotes=[_snapshot()],
        failures=[
            QuoteFailure(
                symbol="600000.SH",
                code="QUOTE_UNAVAILABLE",
                message="Sina returned no current quote for 600000.SH",
            )
        ],
    )


def test_quote_endpoint_returns_snapshot_without_dashboard_calculation(
    monkeypatch,
) -> None:
    monkeypatch.setattr("chan_quant.api.app.fetch_sina_quote", lambda symbol: _snapshot())
    monkeypatch.setattr(
        "chan_quant.api.app.build_dashboard",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("quote endpoint must not build a strategy dashboard")
        ),
    )

    response = TestClient(app).get("/api/v1/instruments/000001.sz/quote")

    assert response.status_code == 200
    assert response.json() == {
        "symbol": "000001.SZ",
        "name": "平安银行",
        "last_price": 11.62,
        "previous_close": 11.48,
        "change": 0.14,
        "change_percent": 0.012195,
        "open": 11.48,
        "high": 11.67,
        "low": 11.42,
        "volume": 63_210_000,
        "quote_at": "2026-07-31T14:35:06+08:00",
        "received_at": "2026-07-31T14:35:07+08:00",
        "source": "sina-undocumented-quote",
        "status": "LIVE",
        "is_stale": False,
    }


def test_batch_quote_endpoint_returns_independent_outcomes_in_one_fetch(
    monkeypatch,
) -> None:
    observed: list[list[str]] = []

    def fake_fetch(symbols: list[str]) -> QuoteBatch:
        observed.append(symbols)
        return _batch()

    monkeypatch.setattr("chan_quant.api.app.fetch_sina_quotes", fake_fetch)

    response = TestClient(app).get(
        "/api/v1/quotes?symbols=000001.sz&symbols=600000.SH"
    )

    assert response.status_code == 200
    assert observed == [["000001.SZ", "600000.SH"]]
    assert response.json() == {
        "status": "PARTIAL",
        "requested": ["000001.SZ", "600000.SH"],
        "succeeded": 1,
        "failed": 1,
        "quotes": [
            {
                "symbol": "000001.SZ",
                "name": "平安银行",
                "last_price": 11.62,
                "previous_close": 11.48,
                "change": 0.14,
                "change_percent": 0.012195,
                "open": 11.48,
                "high": 11.67,
                "low": 11.42,
                "volume": 63_210_000,
                "quote_at": "2026-07-31T14:35:06+08:00",
                "received_at": "2026-07-31T14:35:07+08:00",
                "source": "sina-undocumented-quote",
                "status": "LIVE",
                "is_stale": False,
            }
        ],
        "failures": [
            {
                "symbol": "600000.SH",
                "code": "QUOTE_UNAVAILABLE",
                "message": "Sina returned no current quote for 600000.SH",
            }
        ],
        "source": "sina-undocumented-batch-quote",
    }


@pytest.mark.parametrize(
    ("query", "detail"),
    [
        ("", "batch quote requires 1 to 8 symbols"),
        (
            "?" + "&".join(f"symbols={index:06d}.SZ" for index in range(9)),
            "batch quote requires 1 to 8 symbols",
        ),
        (
            "?symbols=000001.SZ&symbols=000001.sz",
            "batch quote symbols must be distinct",
        ),
    ],
)
def test_batch_quote_endpoint_rejects_invalid_request_shapes(
    query: str, detail: str
) -> None:
    response = TestClient(app).get(f"/api/v1/quotes{query}")

    assert response.status_code == 422
    assert response.json()["detail"] == detail


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (SinaDataError("unsupported symbol"), 422),
        (SinaUpstreamError("Sina quote request returned HTTP 403"), 502),
    ],
)
def test_batch_quote_endpoint_maps_whole_batch_failures(
    monkeypatch,
    error: Exception,
    status_code: int,
) -> None:
    def fail_fetch(symbols: list[str]) -> QuoteBatch:
        del symbols
        raise error

    monkeypatch.setattr("chan_quant.api.app.fetch_sina_quotes", fail_fetch)

    response = TestClient(app).get("/api/v1/quotes?symbols=000001.SZ")

    assert response.status_code == status_code
    assert response.json()["detail"] == str(error)


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (SinaDataError("unsupported symbol"), 422),
        (SinaUpstreamError("Sina quote request returned HTTP 403"), 502),
        (SinaQuoteUnavailableError("Sina returned no current quote"), 503),
    ],
)
def test_quote_endpoint_maps_failure_categories(
    monkeypatch,
    error: Exception,
    status_code: int,
) -> None:
    def fail_fetch(symbol: str) -> QuoteSnapshot:
        del symbol
        raise error

    monkeypatch.setattr("chan_quant.api.app.fetch_sina_quote", fail_fetch)

    response = TestClient(app).get("/api/v1/instruments/000001.sz/quote")

    assert response.status_code == status_code
    assert response.json()["detail"] == str(error)
