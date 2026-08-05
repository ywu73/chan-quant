from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

QuoteStatus = Literal["LIVE", "DELAYED", "CLOSED"]


class QuoteSnapshot(BaseModel):
    """A point-in-time quote that is isolated from daily strategy inputs."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    name: str
    last_price: float
    previous_close: float
    change: float
    change_percent: float
    open: float
    high: float
    low: float
    volume: int
    quote_at: datetime
    received_at: datetime
    source: Literal["sina-undocumented-quote"] = "sina-undocumented-quote"
    status: QuoteStatus
    is_stale: bool


class QuoteFailure(BaseModel):
    """A symbol-scoped quote failure that does not invalidate sibling quotes."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    code: Literal["QUOTE_UNAVAILABLE", "QUOTE_INVALID", "QUOTE_OMITTED"]
    message: str


class QuoteBatch(BaseModel):
    """A single upstream batch normalized into independent quote outcomes."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["COMPLETE", "PARTIAL", "FAILED"]
    requested: list[str] = Field(min_length=1, max_length=8)
    succeeded: int = Field(ge=0)
    failed: int = Field(ge=0)
    quotes: list[QuoteSnapshot]
    failures: list[QuoteFailure]
    source: Literal["sina-undocumented-batch-quote"] = "sina-undocumented-batch-quote"

    @model_validator(mode="after")
    def validate_outcomes(self) -> QuoteBatch:
        if len(set(self.requested)) != len(self.requested):
            raise ValueError("requested quote symbols must be distinct")
        if self.succeeded != len(self.quotes) or self.failed != len(self.failures):
            raise ValueError("quote batch counts must match outcomes")
        if self.succeeded + self.failed != len(self.requested):
            raise ValueError("quote batch outcomes must account for every request")

        outcome_symbols = [quote.symbol for quote in self.quotes] + [
            failure.symbol for failure in self.failures
        ]
        if len(set(outcome_symbols)) != len(outcome_symbols):
            raise ValueError("quote batch outcome symbols must be distinct")
        if set(outcome_symbols) != set(self.requested):
            raise ValueError("quote batch outcomes must match requested symbols")

        expected_status = (
            "COMPLETE"
            if self.failed == 0
            else "FAILED"
            if self.succeeded == 0
            else "PARTIAL"
        )
        if self.status != expected_status:
            raise ValueError("quote batch status must match outcome counts")
        return self
