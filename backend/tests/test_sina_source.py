import json

import httpx
import pytest

from chan_quant.data.sina_source import (
    SINA_KLINE_URL,
    SinaDataError,
    SinaUpstreamError,
    fetch_sina_kline_bars,
    to_sina_symbol,
)


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_sina_symbol_mapping_is_explicit() -> None:
    assert to_sina_symbol("000001.sz") == "sz000001"
    assert to_sina_symbol("600519.SH") == "sh600519"
    with pytest.raises(SinaDataError, match="NNNNNN.SZ"):
        to_sina_symbol("830001.BJ")


def test_sina_kline_source_normalizes_rows_and_request_contract() -> None:
    payload = [
        {
            "day": "2026-07-30",
            "open": "11.280",
            "high": "11.620",
            "low": "11.180",
            "close": "11.610",
            "volume": "277770773",
        },
        {
            "day": "2026-07-29",
            "open": "11.190",
            "high": "11.360",
            "low": "11.180",
            "close": "11.280",
            "volume": "151105407",
        },
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith(SINA_KLINE_URL)
        assert request.url.params["symbol"] == "sz000001"
        assert request.url.params["scale"] == "240"
        assert request.url.params["ma"] == "no"
        assert request.url.params["datalen"] == "2000"
        return httpx.Response(200, content=json.dumps(payload).encode("gb18030"))

    with _client(handler) as client:
        bars = fetch_sina_kline_bars("000001.SZ", client=client)

    assert [bar.date.isoformat() for bar in bars] == ["2026-07-29", "2026-07-30"]
    assert bars[-1].close == 11.61
    assert bars[-1].volume == 277_770_773
    assert bars[-1].amount is None


def test_sina_kline_source_rejects_null_and_input_errors() -> None:
    with (
        _client(lambda _: httpx.Response(200, content=b"null")) as client,
        pytest.raises(SinaDataError, match="no K-line data"),
    ):
        fetch_sina_kline_bars("000001.SZ", client=client)

    error_payload = {"__ERROR": 1, "__ERRORMSG": "Input error"}
    with (
        _client(
            lambda _: httpx.Response(200, content=json.dumps(error_payload).encode())
        ) as client,
        pytest.raises(SinaDataError, match="Input error"),
    ):
        fetch_sina_kline_bars("000001.SZ", client=client)


def test_sina_kline_source_distinguishes_upstream_failures() -> None:
    with (
        _client(lambda _: httpx.Response(403, content=b"Forbidden")) as client,
        pytest.raises(SinaUpstreamError, match="HTTP 403"),
    ):
        fetch_sina_kline_bars("000001.SZ", client=client)

    with (
        _client(lambda _: httpx.Response(200, content=b"not-json")) as client,
        pytest.raises(SinaUpstreamError, match="not valid"),
    ):
        fetch_sina_kline_bars("000001.SZ", client=client)
