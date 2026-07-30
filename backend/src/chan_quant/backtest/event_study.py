from __future__ import annotations

from datetime import timedelta

from chan_quant.domain.dashboard import (
    SidePerformance,
    SignalHorizon,
    SignalPerformance,
)
from chan_quant.domain.market import MarketBar
from chan_quant.domain.strategy import SignalSide, StrategyResult, StrategySignal


def _signals_in_window(
    bars: list[MarketBar], signals: tuple[StrategySignal, ...], lookback_years: int
) -> list[StrategySignal]:
    start_date = bars[-1].date - timedelta(days=365 * lookback_years)
    return [signal for signal in signals if bars[signal.confirmation_index].date >= start_date]


def _side_performance(
    bars: list[MarketBar], signals: list[StrategySignal], side: SignalSide
) -> SidePerformance:
    side_signals = [signal for signal in signals if signal.side is side]
    horizons: list[SignalHorizon] = []
    for horizon in (5, 10, 20):
        returns: list[float] = []
        for signal in side_signals:
            if signal.executable_index is None:
                continue
            target_index = signal.executable_index + horizon - 1
            if target_index >= len(bars):
                continue
            entry_price = bars[signal.executable_index].open
            returns.append(bars[target_index].close / entry_price - 1)

        successes = sum(value > 0 if side is SignalSide.BUY else value < 0 for value in returns)
        eligible = len(returns)
        horizons.append(
            SignalHorizon(
                bars=horizon,
                eligible=eligible,
                successes=successes,
                success_rate=successes / eligible if eligible else 0.0,
                mean_forward_return=sum(returns) / eligible if eligible else 0.0,
            )
        )

    return SidePerformance(
        side=side.value,
        total_signals=len(side_signals),
        horizons=horizons,
        recent_signal_dates=[bars[signal.confirmation_index].date for signal in side_signals[-3:]],
    )


def build_signal_performance(
    bars: list[MarketBar], result: StrategyResult, lookback_years: int = 2
) -> SignalPerformance:
    signals = _signals_in_window(bars, result.signals, lookback_years)
    buy = _side_performance(bars, signals, SignalSide.BUY)
    sell = _side_performance(bars, signals, SignalSide.SELL)
    return SignalPerformance(
        lookback_years=lookback_years,
        headline_total=buy.total_signals + sell.total_signals,
        excluded_total=0,
        excluded_reasons={},
        buy=buy,
        sell=sell,
    )
