import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from chan_quant.api.app import app
from chan_quant.domain.instrument import InstrumentIdentity, normalize_canonical_symbol
from chan_quant.domain.instrument_catalog import resolve_catalog_instrument


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" 000001.sz ", ("000001.SZ", "CN")),
        ("00700.hk", ("00700.HK", "HK")),
        ("aapl.us", ("AAPL.US", "US")),
        ("brk.b.us", ("BRK.B.US", "US")),
        ("spx.gi", ("SPX.GI", "GLOBAL")),
    ],
)
def test_normalize_canonical_symbol_keeps_market_identity_explicit(
    raw: str, expected: tuple[str, str]
) -> None:
    assert normalize_canonical_symbol(raw) == expected


def test_instrument_identity_derives_cn_market_context() -> None:
    instrument = InstrumentIdentity(
        symbol="000001.sz",
        name="平安银行",
        exchange="SZ",
        asset_type="UNKNOWN",
        price_precision=2,
        provider_symbols={" Sina ": "sz000001"},
    )

    assert instrument.model_dump() == {
        "symbol": "000001.SZ",
        "name": "平安银行",
        "exchange": "SZ",
        "asset_type": "UNKNOWN",
        "price_precision": 2,
        "market": "CN",
        "mic": "XSHE",
        "currency": "CNY",
        "timezone": "Asia/Shanghai",
        "trading_calendar": "XSHE",
        "provider_symbols": {"sina": "sz000001"},
    }


def test_instrument_identity_rejects_cross_market_profile_conflicts() -> None:
    with pytest.raises(ValidationError, match="does not belong"):
        InstrumentIdentity(
            symbol="AAPL.US",
            name="Apple Inc.",
            exchange="HKEX",
            asset_type="EQUITY",
            price_precision=2,
            market="US",
        )


def test_catalog_exposes_identity_but_blocks_unapproved_market_data() -> None:
    response = TestClient(app).get("/api/v1/instruments/catalog")

    assert response.status_code == 200
    payload = response.json()
    assert [item["instrument"]["symbol"] for item in payload["items"]] == [
        "00700.HK",
        "AAPL.US",
        "SPX.GI",
    ]
    assert all(
        item["market_data"] == {
            "daily_bars": "BLOCKED",
            "quote": "BLOCKED",
            "reason": "NO_AUTHORIZED_PROVIDER_ADAPTER",
        }
        for item in payload["items"]
    )

    us_response = TestClient(app).get("/api/v1/instruments/catalog", params={"market": "US"})
    assert [item["instrument"]["symbol"] for item in us_response.json()["items"]] == [
        "AAPL.US"
    ]


def test_catalog_identity_resolution_does_not_require_remote_network(monkeypatch) -> None:
    monkeypatch.setenv("CHAN_QUANT_REMOTE_NETWORK_ENABLED", "false")

    response = TestClient(app).get("/api/v1/instruments/aapl.us")

    assert response.status_code == 200
    assert response.json() == resolve_catalog_instrument("AAPL.US").instrument.model_dump()


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/instruments/AAPL.US/dashboard",
        "/api/v1/instruments/AAPL.US/quote",
        "/api/v1/quotes?symbols=AAPL.US",
        "/api/v1/market-comparison?symbols=AAPL.US&symbols=00700.HK",
    ],
)
def test_cross_market_runtime_data_fails_closed(path: str) -> None:
    response = TestClient(app).get(path)

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "MARKET_DATA_ADAPTER_UNAVAILABLE"


def test_uncatalogued_cross_market_identity_is_not_guessed() -> None:
    response = TestClient(app).get("/api/v1/instruments/MSFT.US")

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "IDENTITY_NOT_IN_AUDITED_CATALOG"
