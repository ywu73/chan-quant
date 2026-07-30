from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TrendState = Literal["BULLISH", "BEARISH", "NEUTRAL"]


class StructuralTiming(BaseModel):
    structure_at: datetime
    confirmed_at: datetime
    executable_at: datetime

    @model_validator(mode="after")
    def validate_time_order(self) -> StructuralTiming:
        if not self.structure_at <= self.confirmed_at <= self.executable_at:
            raise ValueError("expected structure_at <= confirmed_at <= executable_at")
        return self


class Instrument(BaseModel):
    symbol: str
    name: str
    timeframe: str
    as_of: date
    last_price: float
    currency: str = "CNY"
    data_updated_at: datetime


class StatusChip(BaseModel):
    label: str
    tone: Literal["neutral", "warning", "danger", "info", "positive"]


class MetricCard(BaseModel):
    key: str
    label: str
    value: str
    detail: str
    tone: Literal["blue", "red", "orange", "purple", "green", "neutral"]


class ReasonItem(BaseModel):
    code: str
    message: str


class WarningItem(BaseModel):
    type: str
    severity: Literal["INFO", "WARNING", "DANGER"]
    message: str


class Recommendation(BaseModel):
    action: Literal["WATCH", "CANDIDATE_BUY", "HOLD", "CANDIDATE_EXIT"]
    title: str
    summary: str
    filter_reasons: list[ReasonItem]
    evidence_lines: list[str]
    warnings: list[WarningItem]


class SignalHorizon(BaseModel):
    bars: int
    eligible: int
    successes: int
    success_rate: float
    mean_forward_return: float

    @model_validator(mode="after")
    def validate_counts(self) -> SignalHorizon:
        if not 0 <= self.successes <= self.eligible:
            raise ValueError("expected successes <= eligible")
        expected = self.successes / self.eligible if self.eligible else 0.0
        if abs(expected - self.success_rate) > 1e-4:
            raise ValueError("success_rate must equal successes / eligible")
        return self


class SidePerformance(BaseModel):
    side: Literal["BUY", "SELL"]
    total_signals: int
    horizons: list[SignalHorizon]
    recent_signal_dates: list[date]


class SignalPerformance(BaseModel):
    lookback_years: int
    headline_total: int
    excluded_total: int
    excluded_reasons: dict[str, int]
    buy: SidePerformance
    sell: SidePerformance

    @model_validator(mode="after")
    def validate_total(self) -> SignalPerformance:
        accounted = self.buy.total_signals + self.sell.total_signals + self.excluded_total
        if self.headline_total != accounted:
            raise ValueError("headline_total must equal buy + sell + excluded")
        return self


class ChartBar(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    buy_line: float
    sell_line: float
    ma57: float


class FractalMarker(BaseModel):
    date: date
    price: float
    kind: Literal["TOP", "BOTTOM"]
    status: Literal["CONFIRMED", "TENTATIVE"] = "CONFIRMED"


class StrokePoint(BaseModel):
    date: date
    price: float


class Stroke(BaseModel):
    direction: Literal["UP", "DOWN"]
    points: list[StrokePoint] = Field(min_length=2, max_length=2)


class SignalMarker(BaseModel):
    id: str
    date: date
    price: float
    side: Literal["BUY", "SELL"]
    label: str
    timing: StructuralTiming
    reasons: list[str]


class ChartSnapshot(BaseModel):
    bars: list[ChartBar]
    fractals: list[FractalMarker]
    strokes: list[Stroke]
    signals: list[SignalMarker]


class StrategyMetadata(BaseModel):
    version: str
    parameter_version: str
    rule_status: Literal["MOCK", "DRAFT", "VALIDATED"]


class DashboardSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_mock: bool
    instrument: Instrument
    status_chips: list[StatusChip]
    metrics: list[MetricCard]
    recommendation: Recommendation
    signal_performance: SignalPerformance
    chart: ChartSnapshot
    strategy: StrategyMetadata
