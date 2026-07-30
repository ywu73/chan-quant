from __future__ import annotations

from dataclasses import dataclass

from chan_quant.domain.market import MarketBar, validate_bar_sequence
from chan_quant.domain.strategy import (
    FractalKind,
    SignalSide,
    StrategyResult,
    StrategySignal,
    StrategyState,
    TrendState,
)
from chan_quant.strategy.indicators import (
    channel_points,
    daily_trends,
    ema,
    sma,
    weekly_trends,
)
from chan_quant.strategy.structures import build_strokes, detect_fractals


@dataclass(frozen=True, slots=True)
class StrategyParameters:
    fast_period: int = 24
    slow_period: int = 90
    trend_period: int = 57
    short_channel_period: int = 24
    long_channel_period: int = 90
    minimum_resonance: int = 2
    cooldown_bars: int = 10
    minimum_stroke_gap: int = 4


def _count_state(target: TrendState, states: tuple[TrendState, ...]) -> int:
    return sum(state is target for state in states)


def run_strategy(
    bars: list[MarketBar], parameters: StrategyParameters | None = None
) -> StrategyResult:
    parameters = parameters or StrategyParameters()
    validate_bar_sequence(bars, minimum=parameters.slow_period + 2)

    closes = [bar.close for bar in bars]
    ema24 = ema(closes, parameters.fast_period)
    ema90 = ema(closes, parameters.slow_period)
    ma57 = sma(closes, parameters.trend_period)
    short_channels = channel_points(bars, parameters.short_channel_period)
    long_channels = channel_points(bars, parameters.long_channel_period)
    daily = daily_trends(bars, ma57)
    weekly = weekly_trends(bars)

    states: list[StrategyState] = []
    for index in range(len(bars)):
        spread = None
        if ema24[index] is not None and ema90[index] is not None:
            spread = ema24[index] / ema90[index] - 1
        directional_states = (
            short_channels[index].state,
            long_channels[index].state,
            daily[index],
            weekly[index].state,
        )
        states.append(
            StrategyState(
                index=index,
                ema24=ema24[index],
                ema90=ema90[index],
                sma57=ma57[index],
                spread_pct=spread,
                short_channel=short_channels[index],
                long_channel=long_channels[index],
                daily_trend=daily[index],
                weekly_trend=weekly[index],
                bullish_resonance=_count_state(TrendState.BULLISH, directional_states),
                bearish_resonance=_count_state(TrendState.BEARISH, directional_states),
            )
        )

    fractals = detect_fractals(bars)
    strokes = build_strokes(fractals, parameters.minimum_stroke_gap)
    candidates: list[StrategySignal] = []

    for fractal_position, fractal in enumerate(fractals):
        last_setup_index = len(bars) - 1
        for later in fractals[fractal_position + 1 :]:
            if later.kind is not fractal.kind:
                last_setup_index = later.confirmation_index - 1
                break
        for index in range(fractal.confirmation_index, last_setup_index + 1):
            if index < 2:
                continue
            current = states[index]
            prior = states[index - 1]
            prior_two = states[index - 2]
            if None in (
                current.ema24,
                prior.ema24,
                current.spread_pct,
                prior.spread_pct,
                prior_two.spread_pct,
            ):
                continue

            if fractal.kind is FractalKind.BOTTOM:
                side = SignalSide.BUY
                line_direction = current.ema24 > prior.ema24
                spread_direction = current.spread_pct > prior.spread_pct > prior_two.spread_pct
                resonance = current.bullish_resonance
                reasons = (
                    "底分型已确认",
                    f"结构确认后第 {index - fractal.confirmation_index} 个交易日触发",
                    "EMA24 上升",
                    "买卖线差连续两日改善",
                    f"多头共振 {resonance}/4",
                )
            else:
                side = SignalSide.SELL
                line_direction = current.ema24 < prior.ema24
                spread_direction = current.spread_pct < prior.spread_pct < prior_two.spread_pct
                resonance = current.bearish_resonance
                reasons = (
                    "顶分型已确认",
                    f"结构确认后第 {index - fractal.confirmation_index} 个交易日触发",
                    "EMA24 下降",
                    "买卖线差连续两日走弱",
                    f"空头共振 {resonance}/4",
                )

            if line_direction and spread_direction and resonance >= parameters.minimum_resonance:
                candidates.append(
                    StrategySignal(
                        id=f"IND-v01-{side.value}-{bars[index].date.isoformat()}",
                        side=side,
                        structure_index=fractal.pivot_index,
                        confirmation_index=index,
                        executable_index=index + 1 if index + 1 < len(bars) else None,
                        reasons=reasons,
                    )
                )
                break

    signals: list[StrategySignal] = []
    last_signal_index: dict[SignalSide, int] = {}
    for candidate in sorted(candidates, key=lambda item: item.confirmation_index):
        previous_signal = last_signal_index.get(candidate.side)
        if (
            previous_signal is not None
            and candidate.confirmation_index - previous_signal < parameters.cooldown_bars
        ):
            continue
        signals.append(candidate)
        last_signal_index[candidate.side] = candidate.confirmation_index

    return StrategyResult(
        states=tuple(states),
        fractals=tuple(fractals),
        strokes=tuple(strokes),
        signals=tuple(signals),
    )
