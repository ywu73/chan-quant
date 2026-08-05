from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from chan_quant.domain.instrument import CurrencyCode, InstrumentIdentity


class ComparisonWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str


class ComparisonFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    code: str
    message: str


class ComparisonSeries(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instrument: InstrumentIdentity
    data_source: str
    adjustment: str
    currency: CurrencyCode
    is_mock: bool
    data_from: date
    data_to: date
    baseline_at: date
    baseline_price: float
    latest_close: float
    previous_trading_day_return: float | None
    values: list[float | None]
    cumulative_return: float
    max_drawdown: float = Field(le=0)
    max_drawdown_peak_at: date | None
    max_drawdown_trough_at: date | None
    coverage_ratio: float = Field(ge=0, le=1)
    warnings: list[ComparisonWarning]


class ComparisonAlignment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_basis: Literal["LOCAL_TRADING_DATE"] = "LOCAL_TRADING_DATE"
    timezone_mode: Literal["PER_INSTRUMENT_IANA"] = "PER_INSTRUMENT_IANA"
    session_scope: Literal["REGULAR_SESSION_CLOSE"] = "REGULAR_SESSION_CLOSE"
    currency_mode: Literal["NATIVE_NO_FX_CONVERSION"] = "NATIVE_NO_FX_CONVERSION"
    missing_date_policy: Literal["NULL_NO_FORWARD_FILL"] = "NULL_NO_FORWARD_FILL"
    overlap_policy: Literal["INTERSECTION_OF_COVERAGE_WINDOWS"] = (
        "INTERSECTION_OF_COVERAGE_WINDOWS"
    )


class MarketComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["COMPLETE", "PARTIAL", "FAILED"]
    requested: list[str]
    succeeded: int = Field(ge=0)
    failed: int = Field(ge=0)
    requested_from: date | None
    requested_to: date | None
    common_from: date | None
    common_to: date | None
    dates: list[date]
    alignment: ComparisonAlignment = Field(default_factory=ComparisonAlignment)
    warnings: list[ComparisonWarning] = Field(default_factory=list)
    series: list[ComparisonSeries]
    failures: list[ComparisonFailure]
