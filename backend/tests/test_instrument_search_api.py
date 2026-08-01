import pytest
from fastapi.testclient import TestClient

from chan_quant.api.app import app
from chan_quant.data.sina_source import SinaDataError, SinaUpstreamError
from chan_quant.domain.instrument import InstrumentIdentity


def test_instrument_search_endpoint_returns_normalized_results(monkeypatch) -> None:
    def fake_search(query: str, *, limit: int) -> list[InstrumentIdentity]:
        assert query == "平安"
        assert limit == 5
        return [
            InstrumentIdentity(
                symbol="000001.SZ",
                name="平安银行",
                exchange="SZ",
                asset_type="UNKNOWN",
                price_precision=2,
            )
        ]

    monkeypatch.setattr("chan_quant.api.app.search_sina_instruments", fake_search)

    response = TestClient(app).get(
        "/api/v1/instruments/search",
        params={"q": " 平安 ", "limit": 5},
    )

    assert response.status_code == 200
    assert response.json() == {
        "query": "平安",
        "items": [
            {
                "symbol": "000001.SZ",
                "name": "平安银行",
                "exchange": "SZ",
                "asset_type": "UNKNOWN",
                "price_precision": 2,
            }
        ],
        "source": "sina-undocumented-suggest",
        "limit": 5,
    }


def test_instrument_identity_endpoint_resolves_canonical_symbol(monkeypatch) -> None:
    expected = InstrumentIdentity(
        symbol="513100.SH",
        name="纳指ETF国泰",
        exchange="SH",
        asset_type="ETF",
        price_precision=3,
    )

    def fake_fetch(symbol: str) -> InstrumentIdentity:
        assert symbol == "513100.sh"
        return expected

    monkeypatch.setattr("chan_quant.api.app.fetch_sina_instrument", fake_fetch)

    response = TestClient(app).get("/api/v1/instruments/513100.sh")

    assert response.status_code == 200
    assert response.json() == expected.model_dump()


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (SinaDataError("invalid query"), 422),
        (SinaUpstreamError("Sina suggest request returned HTTP 403"), 502),
    ],
)
def test_instrument_search_endpoint_maps_failure_categories(
    monkeypatch, error: Exception, status_code: int
) -> None:
    def fail_search(query: str, *, limit: int) -> list[InstrumentIdentity]:
        del query, limit
        raise error

    monkeypatch.setattr("chan_quant.api.app.search_sina_instruments", fail_search)

    response = TestClient(app).get("/api/v1/instruments/search", params={"q": "平安"})

    assert response.status_code == status_code
    assert response.json()["detail"] == str(error)


def test_instrument_search_endpoint_rejects_blank_query() -> None:
    response = TestClient(app).get("/api/v1/instruments/search", params={"q": " "})

    assert response.status_code == 422
    assert response.json()["detail"] == "instrument search query must not be empty"
