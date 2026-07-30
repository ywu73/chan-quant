from __future__ import annotations

import math
from datetime import date, timedelta

from chan_quant.domain.market import MarketBar


def _business_dates_ending(end: date, count: int) -> list[date]:
    dates: list[date] = []
    cursor = end
    while len(dates) < count:
        if cursor.weekday() < 5:
            dates.append(cursor)
        cursor -= timedelta(days=1)
    return list(reversed(dates))


def build_demo_bars(count: int = 620) -> list[MarketBar]:
    dates = _business_dates_ending(date(2026, 7, 30), count)
    bars: list[MarketBar] = []
    for index, trade_date in enumerate(dates):
        trend = 82 + index * 0.055
        cycle = math.sin(index * 0.052) * 17 + math.sin(index * 0.173) * 5.5
        close = max(12.0, trend + cycle)
        open_price = close + math.sin(index * 0.91) * 0.45
        high = max(open_price, close) + 0.65 + abs(math.sin(index * 0.37)) * 0.55
        low = min(open_price, close) - 0.60 - abs(math.cos(index * 0.41)) * 0.50
        volume = int(760_000 + 260_000 * (1 + math.sin(index * 0.29)) + index * 650)
        bars.append(
            MarketBar(
                date=trade_date,
                open=round(open_price, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=volume,
            )
        )
    return bars
