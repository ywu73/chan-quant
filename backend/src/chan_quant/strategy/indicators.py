from __future__ import annotations

from collections import defaultdict

from chan_quant.domain.market import MarketBar
from chan_quant.domain.strategy import ChannelPoint, TrendState, WeeklyTrendPoint


def ema(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result

    seed = sum(values[:period]) / period
    result[period - 1] = seed
    alpha = 2 / (period + 1)
    previous = seed
    for index in range(period, len(values)):
        previous = alpha * values[index] + (1 - alpha) * previous
        result[index] = previous
    return result


def sma(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result

    window_sum = sum(values[:period])
    result[period - 1] = window_sum / period
    for index in range(period, len(values)):
        window_sum += values[index] - values[index - period]
        result[index] = window_sum / period
    return result


def channel_points(bars: list[MarketBar], period: int) -> list[ChannelPoint]:
    if period <= 0:
        raise ValueError("period must be positive")

    state = TrendState.NEUTRAL
    duration = 0
    points: list[ChannelPoint] = []
    for index, bar in enumerate(bars):
        if index < period:
            points.append(ChannelPoint(state=state, duration=duration, upper=None, lower=None))
            continue

        prior_bars = bars[index - period : index]
        upper = max(item.high for item in prior_bars)
        lower = min(item.low for item in prior_bars)
        next_state = state
        if bar.close > upper:
            next_state = TrendState.BULLISH
        elif bar.close < lower:
            next_state = TrendState.BEARISH

        if next_state is TrendState.NEUTRAL:
            duration = 0
        elif next_state is state:
            duration += 1
        else:
            duration = 1
        state = next_state
        points.append(ChannelPoint(state=state, duration=duration, upper=upper, lower=lower))
    return points


def daily_trends(bars: list[MarketBar], ma57: list[float | None]) -> list[TrendState]:
    trends: list[TrendState] = []
    for index, bar in enumerate(bars):
        current = ma57[index]
        prior = ma57[index - 5] if index >= 5 else None
        if current is None or prior is None:
            trends.append(TrendState.NEUTRAL)
        elif bar.close > current > prior:
            trends.append(TrendState.BULLISH)
        elif bar.close < current < prior:
            trends.append(TrendState.BEARISH)
        else:
            trends.append(TrendState.NEUTRAL)
    return trends


def weekly_trends(bars: list[MarketBar]) -> list[WeeklyTrendPoint]:
    groups: dict[tuple[int, int], list[int]] = defaultdict(list)
    ordered_keys: list[tuple[int, int]] = []
    for index, bar in enumerate(bars):
        iso = bar.date.isocalendar()
        key = (iso.year, iso.week)
        if key not in groups:
            ordered_keys.append(key)
        groups[key].append(index)

    weekly_closes = [bars[groups[key][-1]].close for key in ordered_keys]
    fast = ema(weekly_closes, 13)
    slow = ema(weekly_closes, 26)
    group_points: list[WeeklyTrendPoint] = []

    for group_index in range(len(ordered_keys)):
        completed_index = group_index - 1
        if completed_index < 1:
            group_points.append(WeeklyTrendPoint(state=TrendState.NEUTRAL, strong=False))
            continue

        current_fast = fast[completed_index]
        current_slow = slow[completed_index]
        prior_fast = fast[completed_index - 1]
        prior_slow = slow[completed_index - 1]
        if None in (current_fast, current_slow, prior_fast, prior_slow):
            group_points.append(WeeklyTrendPoint(state=TrendState.NEUTRAL, strong=False))
            continue

        close = weekly_closes[completed_index]
        if close > current_fast > current_slow:
            strong = current_fast > prior_fast and current_slow > prior_slow
            group_points.append(WeeklyTrendPoint(state=TrendState.BULLISH, strong=strong))
        elif close < current_fast < current_slow:
            strong = current_fast < prior_fast and current_slow < prior_slow
            group_points.append(WeeklyTrendPoint(state=TrendState.BEARISH, strong=strong))
        else:
            group_points.append(WeeklyTrendPoint(state=TrendState.NEUTRAL, strong=False))

    result = [WeeklyTrendPoint(state=TrendState.NEUTRAL, strong=False)] * len(bars)
    for group_index, key in enumerate(ordered_keys):
        for bar_index in groups[key]:
            result[bar_index] = group_points[group_index]
    return result
