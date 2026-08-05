from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PortfolioPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = "cn-a-fixed-10pct-v1"
    initial_cash: float = Field(default=100_000, gt=0)
    commission_bps: float = Field(default=3, ge=0)
    minimum_commission: float = Field(default=5, ge=0)
    sell_tax_bps: float = Field(default=5, ge=0)
    slippage_bps: float = Field(default=5, ge=0)
    lot_size: int = Field(default=100, ge=1)
    max_position_fraction: float = Field(default=0.95, gt=0, le=1)
    price_limit_ratio: float = Field(default=0.10, gt=0, lt=1)
    price_limit_decimals: int = Field(default=2, ge=0, le=6)


class PortfolioTiming(BaseModel):
    structure_at: date
    confirmed_at: date
    executable_at: date | None

    @model_validator(mode="after")
    def validate_time_order(self) -> PortfolioTiming:
        if self.structure_at > self.confirmed_at:
            raise ValueError("expected structure_at <= confirmed_at")
        if self.executable_at is not None and self.confirmed_at > self.executable_at:
            raise ValueError("expected structure_at <= confirmed_at <= executable_at")
        return self


class PortfolioMarketConstraint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    trading_status: Literal["OPEN", "SUSPENDED"]
    source: str = Field(min_length=1)
    upper_limit: float | None = Field(default=None, gt=0)
    lower_limit: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_limits(self) -> PortfolioMarketConstraint:
        if (
            self.upper_limit is not None
            and self.lower_limit is not None
            and self.lower_limit >= self.upper_limit
        ):
            raise ValueError("expected lower_limit < upper_limit")
        return self


class PortfolioDecision(BaseModel):
    signal_id: str
    side: Literal["BUY", "SELL"]
    status: Literal["FILLED", "REJECTED", "NOT_EXECUTABLE"]
    reason_code: str
    timing: PortfolioTiming
    execution_price: float | None = None
    quantity: int = 0
    notional: float = 0
    commission: float = 0
    transaction_tax: float = 0
    slippage_cost: float = 0
    cash_after: float
    position_after: int


class PortfolioEquityPoint(BaseModel):
    date: date
    cash: float
    position_quantity: int
    close: float
    equity: float


class PortfolioStatistics(BaseModel):
    starting_cash: float
    ending_equity: float
    total_return: float
    max_drawdown: float
    filled_orders: int
    rejected_orders: int
    rejected_reasons: dict[str, int]
    closed_positions: int
    winning_positions: int
    win_rate: float
    total_costs: float
    slippage_cost: float
    turnover: float
    exposure_ratio: float
    open_position_quantity: int
    realized_pnl: float
    unrealized_pnl: float

    @model_validator(mode="after")
    def validate_counts(self) -> PortfolioStatistics:
        if not 0 <= self.winning_positions <= self.closed_positions:
            raise ValueError("expected winning_positions <= closed_positions")
        expected = self.winning_positions / self.closed_positions if self.closed_positions else 0.0
        if abs(expected - self.win_rate) > 1e-8:
            raise ValueError("win_rate must equal winning_positions / closed_positions")
        return self


class PortfolioWarning(BaseModel):
    code: str
    message: str


class PortfolioStudy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    methodology_status: Literal["HYPOTHETICAL_RESEARCH_ASSUMPTIONS"]
    policy: PortfolioPolicy
    market_constraints: list[PortfolioMarketConstraint]
    statistics: PortfolioStatistics
    decisions: list[PortfolioDecision]
    equity_curve: list[PortfolioEquityPoint]
    warnings: list[PortfolioWarning]
