from datetime import date, timedelta

import pytest

from chan_quant.backtest.event_study import build_signal_performance
from chan_quant.domain.market import MarketBar
from chan_quant.domain.strategy import (
    FractalKind,
    SignalSide,
    StrategyResult,
    StrategySignal,
    TrendState,
)
from chan_quant.services.demo_market import build_demo_bars
from chan_quant.strategy.engine import run_strategy
from chan_quant.strategy.indicators import channel_points, ema, sma, weekly_trends
from chan_quant.strategy.structures import detect_fractals


def _bar(index: int, *, open_: float, high: float, low: float, close: float) -> MarketBar:
    return MarketBar(
        date=date(2026, 1, 1) + timedelta(days=index),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=1_000 + index,
    )


def test_ema_and_sma_use_explicit_warmup() -> None:
    values = [1.0, 2.0, 3.0, 4.0]
    assert ema(values, 3) == [None, None, 2.0, 3.0]
    assert sma(values, 3) == [None, None, 2.0, 3.0]


def test_channel_uses_only_prior_bars() -> None:
    bars = [
        _bar(0, open_=8, high=10, low=7, close=9),
        _bar(1, open_=9, high=11, low=8, close=10),
        _bar(2, open_=10, high=12, low=9, close=11),
        _bar(3, open_=11, high=14, low=10, close=13),
    ]
    points = channel_points(bars, 3)
    assert points[3].upper == 12
    assert points[3].state is TrendState.BULLISH
    assert points[3].duration == 1


def test_strict_three_bar_fractals_confirm_on_right_bar() -> None:
    top_bars = [
        _bar(0, open_=7, high=10, low=5, close=8),
        _bar(1, open_=8, high=12, low=6, close=10),
        _bar(2, open_=8, high=11, low=5.5, close=9),
    ]
    bottom_bars = [
        _bar(0, open_=8, high=10, low=5, close=7),
        _bar(1, open_=6, high=9, low=3, close=5),
        _bar(2, open_=7, high=11, low=4, close=8),
    ]

    top = detect_fractals(top_bars)
    bottom = detect_fractals(bottom_bars)
    assert [(item.kind, item.pivot_index, item.confirmation_index) for item in top] == [
        (FractalKind.TOP, 1, 2)
    ]
    assert [(item.kind, item.pivot_index, item.confirmation_index) for item in bottom] == [
        (FractalKind.BOTTOM, 1, 2)
    ]


def test_strategy_signals_are_prefix_stable() -> None:
    bars = build_demo_bars()
    full = run_strategy(bars)
    assert len(full.signals) > 0

    for partial_length in range(92, len(bars) + 1):
        partial = run_strategy(bars[:partial_length])
        partial_identity = [
            (item.id, item.side, item.structure_index, item.confirmation_index)
            for item in partial.signals
        ]
        full_prefix_identity = [
            (item.id, item.side, item.structure_index, item.confirmation_index)
            for item in full.signals
            if item.confirmation_index < partial_length
        ]
        assert partial_identity == full_prefix_identity

        for signal in partial.signals:
            if signal.executable_index is not None:
                matching = next(item for item in full.signals if item.id == signal.id)
                assert signal.executable_index == matching.executable_index


def test_current_week_close_does_not_change_previous_completed_week_state() -> None:
    start = date(2025, 1, 6)
    trade_dates = [
        start + timedelta(days=offset)
        for offset in range(260)
        if (start + timedelta(days=offset)).weekday() < 5
    ][:162]

    def bars_with_last_close(last_close: float) -> list[MarketBar]:
        bars = []
        for index, trade_date in enumerate(trade_dates):
            close = 80 + index * 0.2
            if index == len(trade_dates) - 1:
                close = last_close
            bars.append(
                MarketBar(
                    date=trade_date,
                    open=close,
                    high=close + 1,
                    low=max(0.01, close - 1),
                    close=close,
                    volume=1_000 + index,
                )
            )
        return bars

    low_close_state = weekly_trends(bars_with_last_close(5.0))[-1]
    high_close_state = weekly_trends(bars_with_last_close(500.0))[-1]
    assert low_close_state == high_close_state


def test_event_study_enters_at_next_open_and_counts_execution_bar_in_horizon() -> None:
    bars = [
        _bar(
            index,
            open_=10 + index,
            high=11 + index,
            low=9 + index,
            close=10 + index,
        )
        for index in range(25)
    ]
    signal = StrategySignal(
        id="TEST-BUY",
        side=SignalSide.BUY,
        structure_index=0,
        confirmation_index=1,
        executable_index=2,
        reasons=("test",),
    )
    result = StrategyResult(states=(), fractals=(), strokes=(), signals=(signal,))

    performance = build_signal_performance(bars, result)
    horizon_5 = performance.buy.horizons[0]
    assert horizon_5.bars == 5
    assert horizon_5.eligible == 1
    assert horizon_5.mean_forward_return == pytest.approx(16 / 12 - 1)
    assert horizon_5.successes == 1


def test_market_bar_rejects_invalid_ohlc() -> None:
    with pytest.raises(ValueError, match="OHLC range"):
        _bar(0, open_=10, high=9, low=5, close=8)
