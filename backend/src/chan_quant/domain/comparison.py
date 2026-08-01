from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from chan_quant.domain.instrument import InstrumentIdentity


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
    currency: Literal["CNY"] = "CNY"
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
    series: list[ComparisonSeries]
    failures: list[ComparisonFailure]
