from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TrendState(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class FractalKind(str, Enum):
    TOP = "TOP"
    BOTTOM = "BOTTOM"


class SignalSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True, slots=True)
class Fractal:
    kind: FractalKind
    pivot_index: int
    confirmation_index: int
    price: float


@dataclass(frozen=True, slots=True)
class StrategyStroke:
    direction: str
    start: Fractal
    end: Fractal
    confirmed: bool


@dataclass(frozen=True, slots=True)
class ChannelPoint:
    state: TrendState
    duration: int
    upper: float | None
    lower: float | None


@dataclass(frozen=True, slots=True)
class WeeklyTrendPoint:
    state: TrendState
    strong: bool


@dataclass(frozen=True, slots=True)
class StrategyState:
    index: int
    ema24: float | None
    ema90: float | None
    sma57: float | None
    spread_pct: float | None
    short_channel: ChannelPoint
    long_channel: ChannelPoint
    daily_trend: TrendState
    weekly_trend: WeeklyTrendPoint
    bullish_resonance: int
    bearish_resonance: int


@dataclass(frozen=True, slots=True)
class StrategySignal:
    id: str
    side: SignalSide
    structure_index: int
    confirmation_index: int
    executable_index: int | None
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StrategyResult:
    states: tuple[StrategyState, ...]
    fractals: tuple[Fractal, ...]
    strokes: tuple[StrategyStroke, ...]
    signals: tuple[StrategySignal, ...]
