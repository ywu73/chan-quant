from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest

from chan_quant.data.sina_market_breadth_source import (
    SinaMarketBreadthSourceError,
    fetch_sina_market_breadth,
)

SHANGHAI_TZ = timezone(timedelta(hours=8))


def _quote_line(
    symbol: str,
    *,
    name: str,
    previous_close: str,
    last_price: str,
    quote_date: str = "2026-07-31",
    quote_time: str = "15:01:02",
) -> str:
    fields = [
        name,
        last_price,
        previous_close,
        last_price,
        last_price,
        last_price,
        last_price,
        last_price,
        "100",
        "1000",
        *(["0"] * 20),
        quote_date,
        quote_time,
    ]
    return f'var hq_str_{symbol}="{",".join(fields)}";'


def test_batch_source_returns_requested_quotes_with_provider_dates_and_raw_evidence() -> None:
    requested_at = datetime(2026, 7, 31, 15, 5, tzinfo=SHANGHAI_TZ)
    completed_at = datetime(2026, 7, 31, 15, 5, 1, tzinfo=SHANGHAI_TZ)
    clock_values = iter([requested_at, completed_at])

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://hq.sinajs.cn/?list=sz000001,sh600000"
        assert request.url.params["list"] == "sz000001,sh600000"
        body = "\n".join(
            [
                _quote_line(
                    "sh600000",
                    name="浦发银行",
                    previous_close="9.710",
                    last_price="9.510",
                ),
                _quote_line(
                    "sz000001",
                    name="平安银行",
                    previous_close="11.610",
                    last_price="11.630",
                ),
            ]
        ).encode("gb18030")
        return httpx.Response(200, content=body)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        capture = fetch_sina_market_breadth(
            ["000001.SZ", "600000.SH"],
            session_date=date(2026, 7, 31),
            batch_size=100,
            client=client,
            clock=lambda: next(clock_values),
        )

    assert capture.started_at == requested_at
    assert capture.completed_at == completed_at
    assert capture.request_count == 1
    assert capture.batch_size == 100
    assert len(capture.raw_batches) == 1
    assert [item.symbol for item in capture.observations] == ["000001.SZ", "600000.SH"]
    assert capture.observations[0].session_date == date(2026, 7, 31)
    assert capture.observations[0].previous_close == Decimal("11.610")
    assert capture.observations[0].last_price == Decimal("11.630")
    assert capture.observations[1].previous_close == Decimal("9.710")
    assert capture.observations[1].last_price == Decimal("9.510")


def test_batch_source_retries_a_transient_server_failure_with_a_fixed_limit() -> None:
    observed_at = datetime(2026, 7, 31, 15, 5, tzinfo=SHANGHAI_TZ)
    clock_values = iter([observed_at, observed_at])
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503, text="temporary")
        content = _quote_line(
            "sz000001",
            name="平安银行",
            previous_close="11.610",
            last_price="11.630",
        ).encode("gb18030")
        return httpx.Response(200, content=content)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        capture = fetch_sina_market_breadth(
            ["000001.SZ"],
            session_date=date(2026, 7, 31),
            batch_size=100,
            client=client,
            clock=lambda: next(clock_values),
            sleeper=lambda _: None,
        )

    assert attempts == 2
    assert capture.request_count == 1


def test_batch_source_rejects_an_empty_assignment_without_inferring_its_date() -> None:
    observed_at = datetime(2026, 7, 31, 15, 5, tzinfo=SHANGHAI_TZ)
    clock_values = iter([observed_at, observed_at])

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b'var hq_str_sz000001="";\n')

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(SinaMarketBreadthSourceError) as captured,
    ):
        fetch_sina_market_breadth(
            ["000001.SZ"],
            session_date=date(2026, 7, 31),
            client=client,
            clock=lambda: next(clock_values),
        )

    assert captured.value.code == "SINA_BREADTH_MISSING_QUOTE"
