from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

from chan_quant.backtest.event_study import build_signal_performance
from chan_quant.backtest.portfolio_study import build_portfolio_study
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
    WarningItem,
)
from chan_quant.domain.data_quality import DataQualityReport
from chan_quant.domain.instrument import InstrumentIdentity
from chan_quant.domain.market import MarketBar
from chan_quant.domain.strategy import SignalSide, StrategyResult, TrendState
from chan_quant.strategy.engine import run_strategy

SHANGHAI_TZ = timezone(timedelta(hours=8))


def relative_to_line(current_price: float, line_value: float) -> float:
    return current_price / line_value - 1


def line_spread_pct(buy_line: float, sell_line: float) -> float:
    return buy_line / sell_line - 1


def _market_direction(value: float) -> str:
    if value > 0:
        return "UP"
    if value < 0:
        return "DOWN"
    return "NEUTRAL"


def _trend_text(state: TrendState) -> str:
    return {
        TrendState.BULLISH: "多头",
        TrendState.BEARISH: "空头",
        TrendState.NEUTRAL: "中性",
    }[state]


def _trend_tone(state: TrendState) -> str:
    return (
        "bullish"
        if state is TrendState.BULLISH
        else "bearish"
        if state is TrendState.BEARISH
        else "neutral"
    )


def _regime(short: TrendState, long: TrendState) -> tuple[str, str]:
    if short is long is TrendState.BULLISH:
        return "双多", "bullish"
    if short is long is TrendState.BEARISH:
        return "双空", "bearish"
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
    instrument: InstrumentIdentity,
    is_mock: bool,
    data_source: str,
    adjustment: str,
    data_quality: DataQualityReport | None = None,
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
        zone_label, zone_tone = "强势区", "bullish"
    elif latest.bearish_resonance >= 3:
        zone_label, zone_tone = "弱势区", "bearish"
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
        StatusChip(
            label=action_label,
            tone=(
                "bullish"
                if action == "CANDIDATE_BUY"
                else "bearish"
                if action == "CANDIDATE_EXIT"
                else "warning"
            ),
        ),
        StatusChip(label=zone_label, tone=zone_tone),
        StatusChip(
            label=f"⚡ {direction_label}共振 {dominant_count}/4",
            tone="bullish" if dominant_bullish else "bearish",
        ),
        StatusChip(label=regime_label, tone=regime_tone),
    ]
    if result.signals:
        side_text = "候选买点" if result.signals[-1].side is SignalSide.BUY else "候选退出点"
        status_chips.append(
            StatusChip(
                label=f"{side_text} {signal_age}天前",
                tone="bullish"
                if result.signals[-1].side is SignalSide.BUY
                else "bearish",
            )
        )

    filters = []
    if action == "WATCH":
        filters.append(ReasonItem(code="NO_FRESH_SIGNAL", message="最近 10 个交易日无候选信号"))
    if dominant_count < 2:
        filters.append(ReasonItem(code="LOW_RESONANCE", message="当前多周期共振不足 2/4"))

    warnings: list[WarningItem] = []
    if data_source == "sina-undocumented-kline":
        if instrument.asset_type == "ETF":
            warnings.append(
                WarningItem(
                    type="ETF_ADJUSTMENT_UNVERIFIED",
                    severity="WARNING",
                    message=(
                        "该 ETF 的复权、分红与份额折算口径尚未完成审计；"
                        "原始序列中的机械跳变会直接进入指标、结构、信号和事件研究。"
                    ),
                )
            )
        elif adjustment == "unadjusted-observed":
            warnings.append(
                WarningItem(
                    type="DATA_SOURCE_ADJUSTMENT_UNCONTRACTED",
                    severity="WARNING",
                    message=(
                        "三只股票样本的除权窗口观测与不复权原始行情一致，但新浪没有提供"
                        "固定口径合同；除权除息仍可能制造机械结构和事件信号。"
                    ),
                )
            )
        else:
            warnings.append(
                WarningItem(
                    type="INSTRUMENT_METADATA_UNAVAILABLE",
                    severity="WARNING",
                    message=(
                        "当前标的元数据不可用，行情复权口径未经确认；"
                        "原始序列中的机械跳变可能影响指标、结构和事件研究。"
                    ),
                )
            )

    if data_quality is not None:
        warnings.extend(
            WarningItem(
                type=issue.code,
                severity=issue.severity,
                message=issue.message,
            )
            for issue in data_quality.issues
        )

    precision = instrument.price_precision

    def price(value: float) -> str:
        return f"¥{value:.{precision}f}"

    recommendation = Recommendation(
        action=action,
        title=f"【{action_label}】当前处于{zone_label}，{direction_label}共振 {dominant_count}/4",
        summary=(
            "当前使用合成行情验证 Independent v0.1 规则，不代表真实市场结论。"
            if is_mock
            else (
                (
                    "当前使用新浪财经未文档化 ETF 日 K；复权、分红与份额折算"
                    "口径未经验证，仅供研究审计。"
                    if instrument.asset_type == "ETF"
                    else (
                        "当前使用新浪财经未文档化匿名 K 线端点；有限股票样本"
                        "现场观测为不复权，但没有固定口径合同，仅供研究审计。"
                        if adjustment == "unadjusted-observed"
                        else "当前使用新浪财经未文档化匿名 K 线端点；标的元数据与复权口径未经确认，仅供研究审计。"
                    )
                )
                if data_source == "sina-undocumented-kline"
                else (
                    "当前使用通过 SHA-256 与结构合同校验的本地历史行情快照；"
                    "数据完整性不代表复权经济含义或策略有效性已经验证。"
                    if data_source == "auditable-market-snapshot"
                    else "当前使用外部 CSV 行情和 Independent v0.1 草案规则，仅供研究审计。"
                )
            )
        ),
        filter_reasons=filters,
        evidence_lines=[
            f"EMA24 {price(fast)} vs EMA90 {price(slow)}，差 {fast - slow:+.{precision}f}（{relation}）",
            f"趋势均线 MA57 {price(trend)}，价格在趋势线{'上方' if current_price > trend else '下方'}",
            f"通道：短周期{_trend_text(latest.short_channel.state)} · 长周期{_trend_text(latest.long_channel.state)}",
            f"均线：日线{_trend_text(latest.daily_trend)} · 周线{weekly_label}",
        ],
        warnings=warnings,
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
        data_quality=data_quality,
        instrument=Instrument(
            **instrument.model_dump(),
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
                value=price(fast),
                detail=f"现价 {relative_to_line(current_price, fast):+.2%}",
                tone="blue",
                detail_direction=_market_direction(relative_to_line(current_price, fast)),
            ),
            MetricCard(
                key="sell_line",
                label="卖线 EMA90",
                value=price(slow),
                detail=f"现价 {relative_to_line(current_price, slow):+.2%}",
                tone="red",
                detail_direction=_market_direction(relative_to_line(current_price, slow)),
            ),
            MetricCard(
                key="spread",
                label="买卖线差",
                value=f"{spread:+.2%}",
                detail=relation,
                tone="orange",
                value_direction=_market_direction(spread),
            ),
            MetricCard(
                key="ma57",
                label="趋势线 MA57",
                value=price(trend),
                detail=f"现价 {relative_to_line(current_price, trend):+.2%}",
                tone="purple",
                detail_direction=_market_direction(relative_to_line(current_price, trend)),
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
        portfolio_study=build_portfolio_study(bars, result),
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
