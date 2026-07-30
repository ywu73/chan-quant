from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class MarketBar:
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    amount: float | None = None

    def __post_init__(self) -> None:
        prices = (self.open, self.high, self.low, self.close)
        if not all(math.isfinite(value) and value > 0 for value in prices):
            raise ValueError("OHLC prices must be finite and positive")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("OHLC range does not contain open and close")
        if self.high < self.low:
            raise ValueError("high must be greater than or equal to low")
        if self.volume < 0:
            raise ValueError("volume must be non-negative")
        if self.amount is not None and (not math.isfinite(self.amount) or self.amount < 0):
            raise ValueError("amount must be finite and non-negative")


def validate_bar_sequence(bars: list[MarketBar], *, minimum: int = 1) -> None:
    if len(bars) < minimum:
        raise ValueError(f"expected at least {minimum} bars, got {len(bars)}")
    dates = [bar.date for bar in bars]
    if dates != sorted(dates):
        raise ValueError("bars must be ordered by ascending date")
    if len(set(dates)) != len(dates):
        raise ValueError("bars must not contain duplicate dates")
