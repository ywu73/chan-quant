from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from chan_quant.domain.instrument import InstrumentIdentity, MarketCode


class MarketDataCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    daily_bars: Literal["BLOCKED"] = "BLOCKED"
    quote: Literal["BLOCKED"] = "BLOCKED"
    reason: Literal["NO_AUTHORIZED_PROVIDER_ADAPTER"] = "NO_AUTHORIZED_PROVIDER_ADAPTER"


class CatalogInstrument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instrument: InstrumentIdentity
    identity_source: str
    identity_source_url: str
    confirmed_at: date
    market_data: MarketDataCapability = Field(default_factory=MarketDataCapability)


class InstrumentCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[CatalogInstrument]


_CATALOG: tuple[CatalogInstrument, ...] = (
    CatalogInstrument(
        instrument=InstrumentIdentity(
            symbol="00700.HK",
            name="腾讯控股",
            exchange="HKEX",
            asset_type="EQUITY",
            price_precision=2,
            market="HK",
            provider_symbols={"hkex": "700"},
        ),
        identity_source="Hong Kong Exchanges and Clearing securities quote",
        identity_source_url=(
            "https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities/"
            "Equities-Quote?sym=700&sc_lang=en"
        ),
        confirmed_at=date(2026, 8, 6),
    ),
    CatalogInstrument(
        instrument=InstrumentIdentity(
            symbol="AAPL.US",
            name="Apple Inc.",
            exchange="NASDAQ",
            asset_type="EQUITY",
            price_precision=2,
            market="US",
            provider_symbols={"nasdaq": "AAPL"},
        ),
        identity_source="Nasdaq market activity directory",
        identity_source_url="https://www.nasdaq.com/market-activity/stocks/aapl",
        confirmed_at=date(2026, 8, 6),
    ),
    CatalogInstrument(
        instrument=InstrumentIdentity(
            symbol="SPX.GI",
            name="S&P 500 Index",
            exchange="CBOE",
            asset_type="INDEX",
            price_precision=2,
            market="GLOBAL",
            provider_symbols={"cboe": "SPX"},
        ),
        identity_source="Cboe S&P 500 Index product directory",
        identity_source_url="https://www.cboe.com/tradable_products/sp_500/spx_options/",
        confirmed_at=date(2026, 8, 6),
    ),
)


def list_catalog_instruments(market: MarketCode | None = None) -> list[CatalogInstrument]:
    """Return immutable catalog values through one provider-independent interface."""
    return [
        item.model_copy(deep=True)
        for item in _CATALOG
        if market is None or item.instrument.market == market
    ]


def resolve_catalog_instrument(symbol: str) -> CatalogInstrument | None:
    canonical = symbol.strip().upper()
    return next(
        (item.model_copy(deep=True) for item in _CATALOG if item.instrument.symbol == canonical),
        None,
    )
