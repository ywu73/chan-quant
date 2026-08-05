from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from threading import Barrier

import httpx
from openpyxl import Workbook

from chan_quant.data.exchange_universe_source import fetch_exchange_a_share_universe

SHANGHAI_TZ = timezone(timedelta(hours=8))


def _szse_workbook() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "A股列表"
    sheet.append(["板块", "A股代码", "A股简称", "A股上市日期"])
    sheet.append(["主板", "000001", "平安银行", "1991-04-03"])
    sheet.append(["创业板", "300001", "特锐德", "2009-10-30"])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_exchange_universe_source_combines_official_sse_and_szse_lists() -> None:
    observed_at = datetime(2026, 8, 2, 20, 0, tzinfo=SHANGHAI_TZ)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "query.sse.com.cn":
            stock_type = request.url.params["STOCK_TYPE"]
            row = {
                "A_STOCK_CODE": "600000" if stock_type == "1" else "688001",
                "SEC_NAME_CN": "浦发银行" if stock_type == "1" else "华兴源创",
                "LIST_DATE": "19991110" if stock_type == "1" else "20190722",
                "DELIST_DATE": "-",
            }
            return httpx.Response(200, json={"result": [row]})
        assert request.url.host == "www.szse.cn"
        return httpx.Response(
            200,
            content=_szse_workbook(),
            headers={"Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        capture = fetch_exchange_a_share_universe(
            client=client,
            clock=lambda: observed_at,
            minimum_members=4,
        )

    assert capture.observed_at == observed_at
    assert capture.universe_as_of == date(2026, 8, 2)
    assert capture.universe_id == "sse-szse-live-observed-2026-08-02"
    assert [member.symbol for member in capture.members] == [
        "000001.SZ",
        "300001.SZ",
        "600000.SH",
        "688001.SH",
    ]
    assert [member.board for member in capture.members] == [
        "MAIN",
        "CHINEXT",
        "MAIN",
        "STAR",
    ]


def test_exchange_universe_source_loads_independent_lists_in_parallel() -> None:
    observed_at = datetime(2026, 8, 2, 20, 0, tzinfo=SHANGHAI_TZ)
    barrier = Barrier(3, timeout=2)

    def handler(request: httpx.Request) -> httpx.Response:
        barrier.wait()
        if request.url.host == "query.sse.com.cn":
            stock_type = request.url.params["STOCK_TYPE"]
            row = {
                "A_STOCK_CODE": "600000" if stock_type == "1" else "688001",
                "SEC_NAME_CN": "浦发银行" if stock_type == "1" else "华兴源创",
                "LIST_DATE": "19991110" if stock_type == "1" else "20190722",
                "DELIST_DATE": "-",
            }
            return httpx.Response(200, json={"result": [row]})
        return httpx.Response(200, content=_szse_workbook())

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        capture = fetch_exchange_a_share_universe(
            client=client,
            clock=lambda: observed_at,
            minimum_members=4,
            max_workers=3,
        )

    assert [member.symbol for member in capture.members] == [
        "000001.SZ",
        "300001.SZ",
        "600000.SH",
        "688001.SH",
    ]
