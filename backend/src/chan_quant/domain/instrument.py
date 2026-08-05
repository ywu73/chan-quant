from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AssetType = Literal["EQUITY", "ETF", "INDEX", "UNKNOWN"]
MarketCode = Literal["CN", "HK", "US", "GLOBAL", "SYNTHETIC"]
ExchangeCode = Literal["SZ", "SH", "HKEX", "NASDAQ", "NYSE", "NYSE_ARCA", "CBOE"]
MicCode = Literal["XSHE", "XSHG", "XHKG", "XNAS", "XNYS", "ARCX", "XCBO"]
CurrencyCode = Literal["CNY", "HKD", "USD"]
TradingCalendar = Literal[
    "XSHE",
    "XSHG",
    "XHKG",
    "XNAS",
    "XNYS",
    "ARCX",
    "XCBO",
    "DETERMINISTIC_DEMO",
]

_CN_PATTERN = re.compile(r"^(?P<code>\d{6})\.(?P<exchange>SZ|SH)$")
_HK_PATTERN = re.compile(r"^\d{5}\.HK$")
_US_PATTERN = re.compile(r"^[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)*\.US$")
_GLOBAL_INDEX_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]*\.GI$")

_VENUE_PROFILE: dict[ExchangeCode, tuple[MarketCode, MicCode, CurrencyCode, str, TradingCalendar]] = {
    "SZ": ("CN", "XSHE", "CNY", "Asia/Shanghai", "XSHE"),
    "SH": ("CN", "XSHG", "CNY", "Asia/Shanghai", "XSHG"),
    "HKEX": ("HK", "XHKG", "HKD", "Asia/Hong_Kong", "XHKG"),
    "NASDAQ": ("US", "XNAS", "USD", "America/New_York", "XNAS"),
    "NYSE": ("US", "XNYS", "USD", "America/New_York", "XNYS"),
    "NYSE_ARCA": ("US", "ARCX", "USD", "America/New_York", "ARCX"),
    "CBOE": ("GLOBAL", "XCBO", "USD", "America/New_York", "XCBO"),
}


def normalize_canonical_symbol(value: str) -> tuple[str, MarketCode]:
    """Normalize a provider-neutral symbol without guessing its trading venue."""
    symbol = value.strip().upper()
    if _CN_PATTERN.fullmatch(symbol):
        return symbol, "CN"
    if _HK_PATTERN.fullmatch(symbol):
        return symbol, "HK"
    if _US_PATTERN.fullmatch(symbol):
        return symbol, "US"
    if _GLOBAL_INDEX_PATTERN.fullmatch(symbol):
        return symbol, "GLOBAL"
    raise ValueError(
        "canonical symbol must be NNNNNN.SZ/SH, NNNNN.HK, TICKER.US, or INDEX.GI"
    )


class InstrumentIdentity(BaseModel):
    """Provider-neutral instrument identity and its audited market context."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    name: str
    exchange: ExchangeCode | None
    asset_type: AssetType
    price_precision: int = Field(ge=0, le=6)
    market: MarketCode | None = None
    mic: MicCode | None = None
    currency: CurrencyCode | None = None
    timezone: str | None = None
    trading_calendar: TradingCalendar | None = None
    provider_symbols: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_market_context(self) -> InstrumentIdentity:
        raw_symbol = self.symbol.strip().upper()
        self.symbol = raw_symbol

        try:
            canonical_symbol, inferred_market = normalize_canonical_symbol(raw_symbol)
        except ValueError:
            if self.market not in {None, "SYNTHETIC"}:
                raise
            self.market = "SYNTHETIC"
            self.mic = None
            self.currency = self.currency or "CNY"
            self.timezone = self.timezone or "Asia/Shanghai"
            self.trading_calendar = self.trading_calendar or "DETERMINISTIC_DEMO"
            if self.exchange not in {None, "SZ", "SH"}:
                raise ValueError("synthetic identities cannot claim an external exchange")
            self.provider_symbols = _normalized_provider_symbols(self.provider_symbols)
            return self

        self.symbol = canonical_symbol
        if self.market is not None and self.market != inferred_market:
            raise ValueError("instrument market does not match its canonical symbol")
        self.market = inferred_market

        if inferred_market == "CN":
            match = _CN_PATTERN.fullmatch(canonical_symbol)
            assert match is not None
            expected_exchange = match.group("exchange")
            if self.exchange != expected_exchange:
                raise ValueError("CN instrument exchange must match its canonical symbol suffix")

        if self.exchange is None:
            raise ValueError("non-synthetic instrument identity requires an audited exchange")
        expected = _VENUE_PROFILE[self.exchange]
        expected_market, expected_mic, expected_currency, expected_timezone, expected_calendar = (
            expected
        )
        if inferred_market == "GLOBAL":
            if self.asset_type != "INDEX":
                raise ValueError("INDEX.GI identities must use asset_type=INDEX")
        elif expected_market != inferred_market:
            raise ValueError("instrument exchange does not belong to its canonical market")

        _require_or_fill(self, "mic", expected_mic)
        _require_or_fill(self, "currency", expected_currency)
        _require_or_fill(self, "timezone", expected_timezone)
        _require_or_fill(self, "trading_calendar", expected_calendar)
        self.provider_symbols = _normalized_provider_symbols(self.provider_symbols)
        return self


def _require_or_fill(identity: InstrumentIdentity, field: str, expected: object) -> None:
    actual = getattr(identity, field)
    if actual is not None and actual != expected:
        raise ValueError(f"instrument {field} conflicts with its exchange profile")
    setattr(identity, field, expected)


def _normalized_provider_symbols(symbols: dict[str, str]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for provider, symbol in symbols.items():
        normalized_provider = provider.strip().lower()
        normalized_symbol = symbol.strip()
        if not normalized_provider or not normalized_symbol:
            raise ValueError("provider symbol keys and values must not be blank")
        if normalized_provider in normalized:
            raise ValueError("provider symbol keys must be distinct after normalization")
        normalized[normalized_provider] = normalized_symbol
    return normalized


class InstrumentSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    items: list[InstrumentIdentity]
    source: Literal["sina-undocumented-suggest"] = "sina-undocumented-suggest"
    limit: int = Field(ge=1, le=20)
