from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta, timezone

from chan_quant.domain.dashboard import (
    ChartBar,
    ChartSnapshot,
    DashboardSnapshot,
    FractalMarker,
    Instrument,
    MetricCard,
    ReasonItem,
    Recommendation,
    SidePerformance,
    SignalHorizon,
    SignalMarker,
    SignalPerformance,
    StatusChip,
    StrategyMetadata,
    Stroke,
    StrokePoint,
    StructuralTiming,
    WarningItem,
)

SHANGHAI_TZ = timezone(timedelta(hours=8))


def relative_to_line(current_price: float, line_value: float) -> float:
    return current_price / line_value - 1


def line_spread_pct(buy_line: float, sell_line: float) -> float:
    return buy_line / sell_line - 1


def _business_dates(start: date, count: int) -> list[date]:
    dates: list[date] = []
    cursor = start
    while len(dates) < count:
        if cursor.weekday() < 5:
            dates.append(cursor)
        cursor += timedelta(days=1)
    return dates


def _mock_bars() -> list[ChartBar]:
    dates = _business_dates(date(2026, 4, 27), 69)
    bars: list[ChartBar] = []
    previous_close = 78.0
    final_index = len(dates) - 1

    for index, trade_date in enumerate(dates):
        progress = index / final_index
        if progress <= 0.56:
            center = 78 + (190 - 78) * (progress / 0.56) ** 1.25
        else:
            center = 190 + (108.18 - 190) * ((progress - 0.56) / 0.44)

        close = center + math.sin(index * 0.73) * 4.2
        if index == final_index:
            close = 108.18
        open_price = previous_close + math.sin(index * 1.31) * 2.0
        high = max(open_price, close) + 2.8 + abs(math.sin(index)) * 2.4
        low = min(open_price, close) - 2.5 - abs(math.cos(index)) * 2.1
        volume = int(820_000 + (1 + math.sin(index * 0.47)) * 360_000 + index * 4_100)

        buy_wave = (math.sin(index * 0.16) - math.sin(final_index * 0.16)) * 8
        sell_wave = (math.sin(index * 0.11) - math.sin(final_index * 0.11)) * 25
        ma57_wave = (math.sin(index * 0.08) - math.sin(final_index * 0.08)) * 14
        buy_line = 72 + (102.53 - 72) * progress + buy_wave
        sell_line = 75 + (129.54 - 75) * progress + sell_wave
        ma57 = 68 + (144.85 - 68) * progress + ma57_wave

        bars.append(
            ChartBar(
                date=trade_date,
                open=round(open_price, 2),
                high=round(high, 2),
                low=round(low, 2),
                close=round(close, 2),
                volume=volume,
                buy_line=round(buy_line, 2),
                sell_line=round(sell_line, 2),
                ma57=round(ma57, 2),
            )
        )
        previous_close = close

    return bars


def _timing(bars: list[ChartBar], index: int) -> StructuralTiming:
    structure = datetime.combine(bars[index].date, time(15, 0), SHANGHAI_TZ)
    confirmed = datetime.combine(bars[index + 1].date, time(15, 0), SHANGHAI_TZ)
    executable = datetime.combine(bars[index + 2].date, time(9, 30), SHANGHAI_TZ)
    return StructuralTiming(
        structure_at=structure,
        confirmed_at=confirmed,
        executable_at=executable,
    )


def build_mock_dashboard(symbol: str = "DEMO.SZ") -> DashboardSnapshot:
    bars = _mock_bars()
    current_price = bars[-1].close
    buy_line = bars[-1].buy_line
    sell_line = bars[-1].sell_line
    ma57 = bars[-1].ma57

    pivot_indices = [16, 27, 40, 56]
    pivot_kinds = ["TOP", "BOTTOM", "TOP", "BOTTOM"]
    pivot_prices = [
        bars[i].high if kind == "TOP" else bars[i].low
        for i, kind in zip(pivot_indices, pivot_kinds)
    ]

    fractals = [
        FractalMarker(date=bars[i].date, price=round(price, 2), kind=kind)
        for i, kind, price in zip(pivot_indices, pivot_kinds, pivot_prices)
    ]
    strokes = [
        Stroke(
            direction="DOWN" if pivot_kinds[i] == "TOP" else "UP",
            points=[
                StrokePoint(date=bars[pivot_indices[i]].date, price=round(pivot_prices[i], 2)),
                StrokePoint(
                    date=bars[pivot_indices[i + 1]].date, price=round(pivot_prices[i + 1], 2)
                ),
            ],
        )
        for i in range(len(pivot_indices) - 1)
    ]

    signals = [
        SignalMarker(
            id=f"MOCK-{side}-{bars[index].date.isoformat()}",
            date=bars[index].date,
            price=round(pivot_prices[pivot_index], 2),
            side=side,
            label="买" if side == "BUY" else "卖",
            timing=_timing(bars, index),
            reasons=["MOCK 演示信号", "真实规则尚未确认"],
        )
        for pivot_index, (index, side) in enumerate(
            zip(pivot_indices, ["SELL", "BUY", "SELL", "BUY"])
        )
    ]

    spread = line_spread_pct(buy_line, sell_line)
    price_vs_buy = relative_to_line(current_price, buy_line)
    price_vs_sell = relative_to_line(current_price, sell_line)
    price_vs_ma57 = relative_to_line(current_price, ma57)

    return DashboardSnapshot(
        is_mock=True,
        instrument=Instrument(
            symbol=symbol,
            name="界面演示标的",
            timeframe="1d",
            as_of=bars[-1].date,
            last_price=current_price,
            data_updated_at=datetime.combine(bars[-1].date, time(16, 30), SHANGHAI_TZ),
        ),
        status_chips=[
            StatusChip(label="观望", tone="warning"),
            StatusChip(label="弱势区", tone="danger"),
            StatusChip(label="⚡ 1/4 共振", tone="warning"),
            StatusChip(label="双空", tone="danger"),
            StatusChip(label="一买 9天前", tone="info"),
        ],
        metrics=[
            MetricCard(
                key="buy_line",
                label="买线",
                value=f"¥{buy_line:.2f}",
                detail=f"现价 {price_vs_buy:+.2%}",
                tone="blue",
            ),
            MetricCard(
                key="sell_line",
                label="卖线",
                value=f"¥{sell_line:.2f}",
                detail=f"现价 {price_vs_sell:+.2%}",
                tone="red",
            ),
            MetricCard(
                key="spread",
                label="买卖线差",
                value=f"{spread:+.2%}",
                detail="买线在卖线下方 · 空头",
                tone="orange",
            ),
            MetricCard(
                key="ma57",
                label="趋势线 MA57",
                value=f"¥{ma57:.2f}",
                detail=f"现价 {price_vs_ma57:+.2%}",
                tone="purple",
            ),
            MetricCard(
                key="short_channel",
                label="短通道（24日）",
                value="空头",
                detail="持续 18 天",
                tone="red",
            ),
            MetricCard(
                key="long_channel",
                label="长通道（90日）",
                value="空头",
                detail="持续 3 天",
                tone="red",
            ),
            MetricCard(key="daily_trend", label="日线均线", value="空头", detail="", tone="red"),
            MetricCard(
                key="weekly_trend", label="周线均线", value="空头 · 强势", detail="", tone="red"
            ),
        ],
        recommendation=Recommendation(
            action="WATCH",
            title="【观望】当前处于弱势区，多周期共振 1/4",
            summary="这是 mock 界面状态，不代表真实市场结论。",
            filter_reasons=[ReasonItem(code="NOT_STRONG_ZONE", message="非强势区（弱势区）")],
            evidence_lines=[
                f"买线 ¥{buy_line:.2f} vs 卖线 ¥{sell_line:.2f}，差 {buy_line - sell_line:.2f}（买线在卖线下方 · 空头）",
                f"趋势均线 MA57 ¥{ma57:.2f}，价格在趋势线下方",
                "多空：日线空头 · 周线空头",
            ],
            warnings=[
                WarningItem(
                    type="TOP_DIVERGENCE",
                    severity="WARNING",
                    message="顶背驰（演示）：真实 MACD 背驰规则尚未确认",
                )
            ],
        ),
        signal_performance=SignalPerformance(
            lookback_years=2,
            headline_total=54,
            excluded_total=1,
            excluded_reasons={"insufficient_future_bars": 1},
            buy=SidePerformance(
                side="BUY",
                total_signals=26,
                horizons=[
                    SignalHorizon(
                        bars=5,
                        eligible=26,
                        successes=25,
                        success_rate=25 / 26,
                        mean_forward_return=0.1047,
                    ),
                    SignalHorizon(
                        bars=10,
                        eligible=25,
                        successes=24,
                        success_rate=24 / 25,
                        mean_forward_return=0.1395,
                    ),
                    SignalHorizon(
                        bars=20,
                        eligible=25,
                        successes=21,
                        success_rate=21 / 25,
                        mean_forward_return=0.1748,
                    ),
                ],
                recent_signal_dates=[date(2026, 4, 3), date(2026, 6, 8), date(2026, 7, 21)],
            ),
            sell=SidePerformance(
                side="SELL",
                total_signals=27,
                horizons=[
                    SignalHorizon(
                        bars=5,
                        eligible=27,
                        successes=26,
                        success_rate=26 / 27,
                        mean_forward_return=-0.0991,
                    ),
                    SignalHorizon(
                        bars=10,
                        eligible=27,
                        successes=21,
                        success_rate=21 / 27,
                        mean_forward_return=-0.0759,
                    ),
                    SignalHorizon(
                        bars=20,
                        eligible=27,
                        successes=17,
                        success_rate=17 / 27,
                        mean_forward_return=-0.0400,
                    ),
                ],
                recent_signal_dates=[date(2026, 3, 17), date(2026, 6, 1), date(2026, 6, 22)],
            ),
        ),
        chart=ChartSnapshot(bars=bars, fractals=fractals, strokes=strokes, signals=signals),
        strategy=StrategyMetadata(
            version="chan-v0.1.0-mock", parameter_version="demo-v1", rule_status="MOCK"
        ),
    )
