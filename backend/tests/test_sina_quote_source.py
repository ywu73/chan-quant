from datetime import datetime, timedelta, timezone

import httpx
import pytest

from chan_quant.data.sina_quote_source import (
    SINA_QUOTE_URL,
    SinaQuoteUnavailableError,
    fetch_sina_quote,
    fetch_sina_quotes,
)
from chan_quant.data.sina_source import SinaDataError, SinaUpstreamError

SHANGHAI_TZ = timezone(timedelta(hours=8))


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _quote_content(
    *,
    variable_symbol: str = "sz000001",
    name: str = "平安银行",
    open_price: str = "11.48",
    previous_close: str = "11.48",
    last_price: str = "11.62",
    high: str = "11.67",
    low: str = "11.42",
    volume: str = "63210000",
    quote_date: str = "2026-07-31",
    quote_time: str = "14:35:06",
) -> bytes:
    fields = [
        name,
        open_price,
        previous_close,
        last_price,
        high,
        low,
        "11.61",
        "11.62",
        volume,
        "735000000.00",
        *(["0"] * 20),
        quote_date,
        quote_time,
        "00",
    ]
    return f'var hq_str_{variable_symbol}="{",".join(fields)}";'.encode("gb18030")


def test_sina_quote_source_returns_auditable_snapshot() -> None:
    received_at = datetime(2026, 7, 31, 14, 35, 7, tzinfo=SHANGHAI_TZ)
    content = _quote_content()

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith(SINA_QUOTE_URL)
        assert request.url.params["list"] == "sz000001"
        assert request.headers["Referer"] == "https://finance.sina.com.cn/"
        return httpx.Response(200, content=content)

    with _client(handler) as client:
        quote = fetch_sina_quote(
            "000001.sz",
            client=client,
            received_at=received_at,
        )

    assert quote.symbol == "000001.SZ"
    assert quote.name == "平安银行"
    assert quote.last_price == 11.62
    assert quote.previous_close == 11.48
    assert quote.change == 0.14
    assert quote.change_percent == 0.012195
    assert quote.open == 11.48
    assert quote.high == 11.67
    assert quote.low == 11.42
    assert quote.volume == 63_210_000
    assert quote.quote_at == datetime(2026, 7, 31, 14, 35, 6, tzinfo=SHANGHAI_TZ)
    assert quote.received_at == received_at
    assert quote.source == "sina-undocumented-quote"
    assert quote.status == "LIVE"
    assert quote.is_stale is False


def test_sina_batch_quote_source_uses_one_literal_comma_request_and_requested_order() -> None:
    received_at = datetime(2026, 7, 31, 14, 35, 7, tzinfo=SHANGHAI_TZ)

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://hq.sinajs.cn/?list=sz000001,sh600519"
        content = b"\n".join(
            [
                _quote_content(variable_symbol="sh600519", name="贵州茅台"),
                _quote_content(variable_symbol="sz000001"),
            ]
        )
        return httpx.Response(200, content=content)

    with _client(handler) as client:
        batch = fetch_sina_quotes(
            ["000001.sz", "600519.SH"],
            client=client,
            received_at=received_at,
        )

    assert batch.status == "COMPLETE"
    assert batch.requested == ["000001.SZ", "600519.SH"]
    assert batch.succeeded == 2
    assert batch.failed == 0
    assert [quote.symbol for quote in batch.quotes] == ["000001.SZ", "600519.SH"]
    assert batch.failures == []


def test_sina_batch_quote_source_preserves_valid_siblings_and_classifies_failures() -> None:
    received_at = datetime(2026, 7, 31, 14, 35, 7, tzinfo=SHANGHAI_TZ)
    content = b"\n".join(
        [
            _quote_content(variable_symbol="sz000001"),
            b'var hq_str_sh600519="";',
            _quote_content(variable_symbol="sh600000", last_price="invalid"),
        ]
    )

    with _client(lambda _: httpx.Response(200, content=content)) as client:
        batch = fetch_sina_quotes(
            ["000001.SZ", "600519.SH", "600000.SH", "000002.SZ"],
            client=client,
            received_at=received_at,
        )

    assert batch.status == "PARTIAL"
    assert batch.succeeded == 1
    assert batch.failed == 3
    assert [quote.symbol for quote in batch.quotes] == ["000001.SZ"]
    assert [(failure.symbol, failure.code) for failure in batch.failures] == [
        ("600519.SH", "QUOTE_UNAVAILABLE"),
        ("600000.SH", "QUOTE_INVALID"),
        ("000002.SZ", "QUOTE_OMITTED"),
    ]


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (_quote_content(variable_symbol="sh600000"), "symbol does not match"),
        (
            b"\n".join([_quote_content(), _quote_content()]),
            "duplicate symbol",
        ),
        (b"not-an-assignment", "invalid assignment"),
        (b"\xff\xff", "not valid GB18030"),
    ],
)
def test_sina_batch_quote_source_rejects_batch_contract_violations(
    content: bytes, message: str
) -> None:
    with (
        _client(lambda _: httpx.Response(200, content=content)) as client,
        pytest.raises(SinaUpstreamError, match=message),
    ):
        fetch_sina_quotes(["000001.SZ"], client=client)


@pytest.mark.parametrize(
    ("symbols", "message"),
    [
        ([], "1 to 8"),
        (["000001.SZ"] * 9, "1 to 8"),
        (["000001.SZ", "000001.sz"], "distinct"),
        (["AAPL.US"], "NNNNNN.SZ"),
    ],
)
def test_sina_batch_quote_source_rejects_invalid_requests(
    symbols: list[str], message: str
) -> None:
    with pytest.raises(SinaDataError, match=message):
        fetch_sina_quotes(symbols)


def test_sina_quote_source_classifies_empty_snapshot_as_unavailable() -> None:
    with (
        _client(
            lambda _: httpx.Response(200, content=b'var hq_str_sz000001="";')
        ) as client,
        pytest.raises(SinaQuoteUnavailableError, match="no current quote"),
    ):
        fetch_sina_quote("000001.SZ", client=client)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (_quote_content(variable_symbol="sh600519"), "symbol does not match"),
        (b'var hq_str_sz000001="only,two";', "fewer than 32 fields"),
        (_quote_content(last_price="not-a-number"), "last_price is not numeric"),
        (_quote_content(quote_date="2026-02-30"), "date or time is invalid"),
        (b"\xff\xff", "not valid GB18030"),
    ],
)
def test_sina_quote_source_rejects_malformed_payloads(
    content: bytes, message: str
) -> None:
    with (
        _client(lambda _: httpx.Response(200, content=content)) as client,
        pytest.raises(SinaUpstreamError, match=message),
    ):
        fetch_sina_quote("000001.SZ", client=client)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (_quote_content(name=""), "name is empty"),
        (_quote_content(previous_close="0"), "previous_close must be positive"),
        (_quote_content(last_price="-1"), "last_price must be positive"),
        (_quote_content(high="11.40", low="11.70"), "OHLC range is invalid"),
        (_quote_content(volume="12.5"), "volume must be a non-negative integer"),
    ],
)
def test_sina_quote_source_validates_quote_values(
    content: bytes, message: str
) -> None:
    with (
        _client(lambda _: httpx.Response(200, content=content)) as client,
        pytest.raises(SinaUpstreamError, match=message),
    ):
        fetch_sina_quote("000001.SZ", client=client)


def test_sina_quote_source_classifies_zero_snapshot_as_unavailable() -> None:
    content = _quote_content(
        open_price="0",
        previous_close="0",
        last_price="0",
        high="0",
        low="0",
        volume="0",
    )
    with (
        _client(lambda _: httpx.Response(200, content=content)) as client,
        pytest.raises(SinaQuoteUnavailableError, match="zero-valued quote"),
    ):
        fetch_sina_quote("000001.SZ", client=client)


def test_sina_quote_source_classifies_zero_range_snapshot_as_unavailable() -> None:
    content = _quote_content(
        open_price="0",
        high="0",
        low="0",
        volume="0",
    )
    with (
        _client(lambda _: httpx.Response(200, content=content)) as client,
        pytest.raises(SinaQuoteUnavailableError, match="zero-range quote"),
    ):
        fetch_sina_quote("000001.SZ", client=client)


def test_sina_quote_source_rejects_quote_time_after_receive_time() -> None:
    received_at = datetime(2026, 7, 31, 14, 34, 0, tzinfo=SHANGHAI_TZ)
    with (
        _client(lambda _: httpx.Response(200, content=_quote_content())) as client,
        pytest.raises(SinaUpstreamError, match="later than received_at"),
    ):
        fetch_sina_quote(
            "000001.SZ",
            client=client,
            received_at=received_at,
        )


@pytest.mark.parametrize(
    ("quote_date", "quote_time", "received_at", "status", "is_stale"),
    [
        (
            "2026-07-31",
            "14:34:00",
            datetime(2026, 7, 31, 14, 35, 7, tzinfo=SHANGHAI_TZ),
            "DELAYED",
            True,
        ),
        (
            "2026-07-31",
            "15:00:00",
            datetime(2026, 7, 31, 15, 1, 0, tzinfo=SHANGHAI_TZ),
            "CLOSED",
            False,
        ),
        (
            "2026-07-30",
            "14:59:59",
            datetime(2026, 7, 31, 9, 0, 0, tzinfo=SHANGHAI_TZ),
            "CLOSED",
            False,
        ),
    ],
)
def test_sina_quote_source_classifies_freshness(
    quote_date: str,
    quote_time: str,
    received_at: datetime,
    status: str,
    is_stale: bool,
) -> None:
    content = _quote_content(quote_date=quote_date, quote_time=quote_time)
    with _client(lambda _: httpx.Response(200, content=content)) as client:
        quote = fetch_sina_quote(
            "000001.SZ",
            client=client,
            received_at=received_at,
        )

    assert quote.status == status
    assert quote.is_stale is is_stale


def test_sina_quote_source_classifies_http_and_transport_failures() -> None:
    with (
        _client(lambda _: httpx.Response(403, content=b"Forbidden")) as client,
        pytest.raises(SinaUpstreamError, match="HTTP 403"),
    ):
        fetch_sina_quote("000001.SZ", client=client)

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with (
        _client(timeout) as client,
        pytest.raises(SinaUpstreamError, match="request failed: timed out"),
    ):
        fetch_sina_quote("000001.SZ", client=client)
