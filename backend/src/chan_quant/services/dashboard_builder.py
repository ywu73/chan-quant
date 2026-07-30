from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

from chan_quant.backtest.event_study import build_signal_performance
from chan_quant.domain.dashboard import (
    ChartBar,
    ChartSnapshot,
    DashboardSnapshot,
    FractalMarker,
    Instrument,
    MetricCard,
    ReasonItem,
    Recommendation,
    SignalMarker,
    StatusChip,
    StrategyMetadata,
    Stroke,
    StrokePoint,
    StructuralTiming,
)
from chan_quant.domain.market import MarketBar
from chan_quant.domain.strategy import SignalSide, StrategyResult, TrendState
from chan_quant.strategy.engine import run_strategy

SHANGHAI_TZ = timezone(timedelta(hours=8))


def relative_to_line(current_price: float, line_value: float) -> float:
    return current_price / line_value - 1


def line_spread_pct(buy_line: float, sell_line: float) -> float:
    return buy_line / sell_line - 1


def _trend_text(state: TrendState) -> str:
    return {
        TrendState.BULLISH: "多头",
        TrendState.BEARISH: "空头",
        TrendState.NEUTRAL: "中性",
    }[state]


def _trend_tone(state: TrendState) -> str:
    return (
        "green"
        if state is TrendState.BULLISH
        else "red"
        if state is TrendState.BEARISH
        else "neutral"
    )


def _regime(short: TrendState, long: TrendState) -> tuple[str, str]:
    if short is long is TrendState.BULLISH:
        return "双多", "positive"
    if short is long is TrendState.BEARISH:
        return "双空", "danger"
    return "通道分歧", "warning"


def _timing(bars: list[MarketBar], signal) -> StructuralTiming:
    executable = None
    if signal.executable_index is not None:
        executable = datetime.combine(bars[signal.executable_index].date, time(9, 30), SHANGHAI_TZ)
    return StructuralTiming(
        structure_at=datetime.combine(bars[signal.structure_index].date, time(15, 0), SHANGHAI_TZ),
        confirmed_at=datetime.combine(
            bars[signal.confirmation_index].date, time(15, 0), SHANGHAI_TZ
        ),
        executable_at=executable,
    )


def _action(result: StrategyResult, bar_count: int) -> tuple[str, str, int | None]:
    if not result.signals:
        return "WATCH", "观望", None
    latest = result.signals[-1]
    age = bar_count - 1 - latest.confirmation_index
    if age <= 10 and latest.side is SignalSide.BUY:
        return "CANDIDATE_BUY", "候选买入", age
    if age <= 10 and latest.side is SignalSide.SELL:
        return "CANDIDATE_EXIT", "候选退出", age
    return "WATCH", "观望", age


def build_dashboard(
    bars: list[MarketBar],
    *,
    symbol: str,
    name: str,
    is_mock: bool,
    data_source: str,
    adjustment: str,
) -> DashboardSnapshot:
    result = run_strategy(bars)
    latest = result.states[-1]
    current_price = bars[-1].close
    if latest.ema24 is None or latest.ema90 is None or latest.sma57 is None:
        raise ValueError("insufficient history for EMA90 and MA57")

    action, action_label, signal_age = _action(result, len(bars))
    dominant_bullish = latest.bullish_resonance >= latest.bearish_resonance
    dominant_count = max(latest.bullish_resonance, latest.bearish_resonance)
    direction_label = "多头" if dominant_bullish else "空头"
    if latest.bullish_resonance >= 3:
        zone_label, zone_tone = "强势区", "positive"
    elif latest.bearish_resonance >= 3:
        zone_label, zone_tone = "弱势区", "danger"
    else:
        zone_label, zone_tone = "中性区", "warning"
    regime_label, regime_tone = _regime(latest.short_channel.state, latest.long_channel.state)

    fast = latest.ema24
    slow = latest.ema90
    trend = latest.sma57
    spread = line_spread_pct(fast, slow)
    relation = "买线在卖线上方 · 多头" if spread > 0 else "买线在卖线下方 · 空头"
    weekly_label = _trend_text(latest.weekly_trend.state)
    if latest.weekly_trend.strong and latest.weekly_trend.state is not TrendState.NEUTRAL:
        weekly_label += " · 强势"

    status_chips = [
        StatusChip(label=action_label, tone="info" if action != "WATCH" else "warning"),
        StatusChip(label=zone_label, tone=zone_tone),
        StatusChip(label=f"⚡ {direction_label}共振 {dominant_count}/4", tone="warning"),
        StatusChip(label=regime_label, tone=regime_tone),
    ]
    if result.signals:
        side_text = "候选买点" if result.signals[-1].side is SignalSide.BUY else "候选退出点"
        status_chips.append(StatusChip(label=f"{side_text} {signal_age}天前", tone="info"))

    filters = []
    if action == "WATCH":
        filters.append(ReasonItem(code="NO_FRESH_SIGNAL", message="最近 10 个交易日无候选信号"))
    if dominant_count < 2:
        filters.append(ReasonItem(code="LOW_RESONANCE", message="当前多周期共振不足 2/4"))

    recommendation = Recommendation(
        action=action,
        title=f"【{action_label}】当前处于{zone_label}，{direction_label}共振 {dominant_count}/4",
        summary=(
            "当前使用合成行情验证 Independent v0.1 规则，不代表真实市场结论。"
            if is_mock
            else "当前使用外部 CSV 行情和 Independent v0.1 草案规则，仅供研究审计。"
        ),
        filter_reasons=filters,
        evidence_lines=[
            f"EMA24 ¥{fast:.2f} vs EMA90 ¥{slow:.2f}，差 {fast - slow:+.2f}（{relation}）",
            f"趋势均线 MA57 ¥{trend:.2f}，价格在趋势线{'上方' if current_price > trend else '下方'}",
            f"通道：短周期{_trend_text(latest.short_channel.state)} · 长周期{_trend_text(latest.long_channel.state)}",
            f"均线：日线{_trend_text(latest.daily_trend)} · 周线{weekly_label}",
        ],
        warnings=[],
    )

    chart_start = max(0, len(bars) - 180)
    chart_bars = [
        ChartBar(
            date=bar.date,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            buy_line=round(result.states[index].ema24, 4)
            if result.states[index].ema24 is not None
            else None,
            sell_line=round(result.states[index].ema90, 4)
            if result.states[index].ema90 is not None
            else None,
            ma57=round(result.states[index].sma57, 4)
            if result.states[index].sma57 is not None
            else None,
        )
        for index, bar in enumerate(bars)
        if index >= chart_start
    ]
    fractals = [
        FractalMarker(
            date=bars[item.pivot_index].date,
            price=item.price,
            kind=item.kind.value,
        )
        for item in result.fractals
        if item.pivot_index >= chart_start
    ]
    strokes = [
        Stroke(
            direction=item.direction,
            points=[
                StrokePoint(date=bars[item.start.pivot_index].date, price=item.start.price),
                StrokePoint(date=bars[item.end.pivot_index].date, price=item.end.price),
            ],
            status="CONFIRMED" if item.confirmed else "TENTATIVE",
        )
        for item in result.strokes
        if item.start.pivot_index >= chart_start
    ]
    signals = [
        SignalMarker(
            id=item.id,
            date=bars[item.structure_index].date,
            price=(
                bars[item.structure_index].low
                if item.side is SignalSide.BUY
                else bars[item.structure_index].high
            ),
            side=item.side.value,
            label="买" if item.side is SignalSide.BUY else "卖",
            timing=_timing(bars, item),
            reasons=list(item.reasons),
        )
        for item in result.signals
        if item.structure_index >= chart_start
    ]

    return DashboardSnapshot(
        is_mock=is_mock,
        instrument=Instrument(
            symbol=symbol,
            name=name,
            timeframe="1d",
            as_of=bars[-1].date,
            last_price=current_price,
            data_updated_at=datetime.combine(bars[-1].date, time(16, 30), SHANGHAI_TZ),
            data_source=data_source,
            adjustment=adjustment,
        ),
        status_chips=status_chips,
        metrics=[
            MetricCard(
                key="buy_line",
                label="买线 EMA24",
                value=f"¥{fast:.2f}",
                detail=f"现价 {relative_to_line(current_price, fast):+.2%}",
                tone="blue",
            ),
            MetricCard(
                key="sell_line",
                label="卖线 EMA90",
                value=f"¥{slow:.2f}",
                detail=f"现价 {relative_to_line(current_price, slow):+.2%}",
                tone="red",
            ),
            MetricCard(
                key="spread",
                label="买卖线差",
                value=f"{spread:+.2%}",
                detail=relation,
                tone="orange",
            ),
            MetricCard(
                key="ma57",
                label="趋势线 MA57",
                value=f"¥{trend:.2f}",
                detail=f"现价 {relative_to_line(current_price, trend):+.2%}",
                tone="purple",
            ),
            MetricCard(
                key="short_channel",
                label="短通道（24日）",
                value=_trend_text(latest.short_channel.state),
                detail=f"持续 {latest.short_channel.duration} 天",
                tone=_trend_tone(latest.short_channel.state),
            ),
            MetricCard(
                key="long_channel",
                label="长通道（90日）",
                value=_trend_text(latest.long_channel.state),
                detail=f"持续 {latest.long_channel.duration} 天",
                tone=_trend_tone(latest.long_channel.state),
            ),
            MetricCard(
                key="daily_trend",
                label="日线均线",
                value=_trend_text(latest.daily_trend),
                detail="MA57 位置与 5 日斜率",
                tone=_trend_tone(latest.daily_trend),
            ),
            MetricCard(
                key="weekly_trend",
                label="周线均线",
                value=weekly_label,
                detail="EMA13 / EMA26",
                tone=_trend_tone(latest.weekly_trend.state),
            ),
        ],
        recommendation=recommendation,
        signal_performance=build_signal_performance(bars, result),
        chart=ChartSnapshot(
            bars=chart_bars,
            fractals=fractals,
            strokes=strokes,
            signals=signals,
        ),
        strategy=StrategyMetadata(
            version="independent-v0.1.0",
            parameter_version="ema24-ema90-ma57-donchian24-90-r2",
            rule_status="DRAFT",
        ),
    )
