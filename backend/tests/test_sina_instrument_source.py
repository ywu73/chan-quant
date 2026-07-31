import httpx
import pytest

from chan_quant.data.sina_instrument_source import (
    SINA_SUGGEST_URL,
    fetch_sina_instrument,
    search_sina_instruments,
)
from chan_quant.data.sina_source import SinaDataError, SinaUpstreamError


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _content(records: str) -> bytes:
    return f'var chan_quant_suggest="{records}";'.encode("gb18030")


def test_search_sina_instruments_returns_normalized_shenzhen_and_shanghai_items() -> None:
    content = _content(
        "中国平安,11,601318,sh601318,中国平安,,中国平安,99,1,ESG,,;"
        "平安银行,11,000001,sz000001,平安银行,,平安银行,99,1,ESG,,"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith(SINA_SUGGEST_URL)
        assert request.url.params["type"] == "11,203"
        assert request.url.params["key"] == "平安"
        assert request.url.params["name"] == "chan_quant_suggest"
        assert request.headers["Referer"] == "https://finance.sina.com.cn/"
        return httpx.Response(200, content=content)

    with _client(handler) as client:
        items = search_sina_instruments("  平安  ", client=client)

    assert [item.model_dump() for item in items] == [
        {
            "symbol": "601318.SH",
            "name": "中国平安",
            "exchange": "SH",
            "asset_type": "UNKNOWN",
            "price_precision": 2,
        },
        {
            "symbol": "000001.SZ",
            "name": "平安银行",
            "exchange": "SZ",
            "asset_type": "UNKNOWN",
            "price_precision": 2,
        },
    ]


def test_search_sina_instruments_filters_other_categories_and_deduplicates() -> None:
    content = _content(
        "平安银行,11,000001,sz000001,平安银行,,平安银行,99,1,,,;"
        "平安银行,11,000001,sz000001,平安银行,,平安银行,99,1,,,;"
        "港股示例,31,00001,hk00001,港股示例,,港股示例,99,1,,,;"
        "场外基金,22,513100,of513100,纳指ETF国泰,,纳指ETF国泰,99,1,,,;"
        "贵州茅台,11,600519,sh600519,贵州茅台,,贵州茅台,99,1,,,"
    )

    with _client(lambda _: httpx.Response(200, content=content)) as client:
        items = search_sina_instruments("测试", limit=1, client=client)

    assert [item.symbol for item in items] == ["000001.SZ"]


def test_search_sina_instruments_returns_empty_results() -> None:
    with _client(lambda _: httpx.Response(200, content=_content(""))) as client:
        assert search_sina_instruments("不存在", client=client) == []


def test_search_sina_instruments_classifies_exchange_traded_funds() -> None:
    content = _content(
        "纳指ETF国泰,203,513100,sh513100,纳指ETF国泰,,纳指ETF国泰,99,1,,,;"
        "创业板ETF易方达,203,159915,sz159915,创业板ETF易方达,,创业板ETF易方达,99,1,,,"
    )

    with _client(lambda _: httpx.Response(200, content=content)) as client:
        items = search_sina_instruments("ETF", client=client)

    assert [item.model_dump() for item in items] == [
        {
            "symbol": "513100.SH",
            "name": "纳指ETF国泰",
            "exchange": "SH",
            "asset_type": "ETF",
            "price_precision": 3,
        },
        {
            "symbol": "159915.SZ",
            "name": "创业板ETF易方达",
            "exchange": "SZ",
            "asset_type": "ETF",
            "price_precision": 3,
        },
    ]


def test_fetch_sina_instrument_requires_exact_symbol_match() -> None:
    content = _content(
        "sh000001,11,000001,sh000001,上证指数,,上证指数,99,1,,,;"
        "sz000001,11,000001,sz000001,平安银行,,平安银行,99,1,,,"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["key"] == "sz000001"
        return httpx.Response(200, content=content)

    with _client(handler) as client:
        instrument = fetch_sina_instrument("000001.sz", client=client)

    assert instrument.symbol == "000001.SZ"
    assert instrument.name == "平安银行"
    assert instrument.asset_type == "UNKNOWN"
    assert instrument.price_precision == 2


def test_fetch_sina_instrument_returns_etf_metadata() -> None:
    content = _content("sh513100,203,513100,sh513100,纳指ETF国泰,,纳指ETF国泰,99,1,,,")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["key"] == "sh513100"
        return httpx.Response(200, content=content)

    with _client(handler) as client:
        instrument = fetch_sina_instrument("513100.SH", client=client)

    assert instrument.model_dump() == {
        "symbol": "513100.SH",
        "name": "纳指ETF国泰",
        "exchange": "SH",
        "asset_type": "ETF",
        "price_precision": 3,
    }


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b'var wrong_name="";', "invalid assignment"),
        (b"\xff\xff", "not valid GB18030"),
        (_content("broken,row"), "fewer than 5 fields"),
        (
            _content("平安银行,11,000002,sz000001,平安银行"),
            "code does not match",
        ),
        (_content("平安银行,11,000001,sz000001,"), "name is empty"),
    ],
)
def test_search_sina_instruments_rejects_malformed_payloads(content: bytes, message: str) -> None:
    with (
        _client(lambda _: httpx.Response(200, content=content)) as client,
        pytest.raises(SinaUpstreamError, match=message),
    ):
        search_sina_instruments("平安", client=client)


def test_search_sina_instruments_validates_inputs_and_upstream_status() -> None:
    with pytest.raises(SinaDataError, match="must not be empty"):
        search_sina_instruments(" ")

    with (
        _client(lambda _: httpx.Response(403, content=b"Forbidden")) as client,
        pytest.raises(SinaUpstreamError, match="HTTP 403"),
    ):
        search_sina_instruments("平安", client=client)
