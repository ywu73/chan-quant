from datetime import date, timedelta

import pytest

from chan_quant.backtest.portfolio_study import build_portfolio_study
from chan_quant.domain.market import MarketBar
from chan_quant.domain.portfolio import PortfolioMarketConstraint, PortfolioPolicy
from chan_quant.domain.strategy import SignalSide, StrategyResult, StrategySignal


def _bar(
    index: int,
    *,
    open_: float,
    high: float | None = None,
    low: float | None = None,
    close: float | None = None,
    volume: int = 10_000,
) -> MarketBar:
    close = open_ if close is None else close
    return MarketBar(
        date=date(2026, 1, 1) + timedelta(days=index),
        open=open_,
        high=max(open_, close) + 1 if high is None else high,
        low=min(open_, close) - 1 if low is None else low,
        close=close,
        volume=volume,
    )


def _signal(
    side: SignalSide,
    *,
    structure: int,
    confirmed: int,
    executable: int | None,
) -> StrategySignal:
    return StrategySignal(
        id=f"TEST-{side.value}-{confirmed}",
        side=side,
        structure_index=structure,
        confirmation_index=confirmed,
        executable_index=executable,
        reasons=("test",),
    )


def _result(*signals: StrategySignal) -> StrategyResult:
    return StrategyResult(states=(), fractals=(), strokes=(), signals=signals)


def _policy(**overrides: float) -> PortfolioPolicy:
    values = {
        "initial_cash": 10_000,
        "commission_bps": 10,
        "minimum_commission": 0,
        "sell_tax_bps": 10,
        "slippage_bps": 0,
        "lot_size": 100,
        "max_position_fraction": 1,
        "price_limit_ratio": 0.10,
        "price_limit_decimals": 2,
    }
    values.update(overrides)
    return PortfolioPolicy(**values)


def test_portfolio_study_executes_next_open_with_costs_lots_and_timing() -> None:
    bars = [
        _bar(0, open_=10, close=10),
        _bar(1, open_=10, close=10),
        _bar(2, open_=10, close=11),
        _bar(3, open_=12, close=12),
        _bar(4, open_=12, close=12),
    ]
    result = _result(
        _signal(SignalSide.BUY, structure=0, confirmed=1, executable=2),
        _signal(SignalSide.SELL, structure=2, confirmed=2, executable=3),
    )

    study = build_portfolio_study(bars, result, _policy())

    buy, sell = study.decisions
    assert buy.status == "FILLED"
    assert buy.execution_price == 10
    assert buy.quantity == 900
    assert buy.commission == 9
    assert buy.cash_after == 991
    assert buy.position_after == 900
    assert buy.timing.structure_at == bars[0].date
    assert buy.timing.confirmed_at == bars[1].date
    assert buy.timing.executable_at == bars[2].date

    assert sell.status == "FILLED"
    assert sell.execution_price == 12
    assert sell.commission == pytest.approx(10.8)
    assert sell.transaction_tax == pytest.approx(10.8)
    assert sell.position_after == 0
    assert study.statistics.closed_positions == 1
    assert study.statistics.winning_positions == 1
    assert study.statistics.total_costs == pytest.approx(30.6)
    assert study.statistics.ending_equity == pytest.approx(11_769.4)
    assert study.statistics.total_return == pytest.approx(0.17694)


def test_portfolio_study_blocks_zero_volume_and_fixed_limit_orders() -> None:
    bars = [
        _bar(0, open_=10, close=10),
        _bar(1, open_=11, high=11, low=11, close=11),
        _bar(2, open_=10, close=10, volume=0),
        _bar(3, open_=10, close=10),
    ]
    result = _result(
        _signal(SignalSide.BUY, structure=0, confirmed=0, executable=1),
        _signal(SignalSide.BUY, structure=0, confirmed=1, executable=2),
    )

    study = build_portfolio_study(bars, result, _policy())

    assert [decision.reason_code for decision in study.decisions] == [
        "PRICE_LIMIT_UP",
        "ZERO_VOLUME",
    ]
    assert study.statistics.filled_orders == 0
    assert study.statistics.rejected_orders == 2
    assert study.statistics.rejected_reasons == {
        "PRICE_LIMIT_UP": 1,
        "ZERO_VOLUME": 1,
    }


def test_portfolio_study_uses_explicit_suspension_and_limit_evidence() -> None:
    bars = [
        _bar(0, open_=10, close=10),
        _bar(1, open_=10, close=10),
        _bar(2, open_=10.5, close=10.5),
    ]
    result = _result(
        _signal(SignalSide.BUY, structure=0, confirmed=0, executable=1),
        _signal(SignalSide.BUY, structure=0, confirmed=1, executable=2),
    )
    constraints = (
        PortfolioMarketConstraint(
            date=bars[1].date,
            trading_status="SUSPENDED",
            source="licensed-status-sample",
        ),
        PortfolioMarketConstraint(
            date=bars[2].date,
            trading_status="OPEN",
            source="licensed-limit-sample",
            upper_limit=10.5,
            lower_limit=9.5,
        ),
    )

    study = build_portfolio_study(
        bars,
        result,
        _policy(),
        market_constraints=constraints,
    )

    assert [decision.reason_code for decision in study.decisions] == [
        "SUSPENDED",
        "PRICE_LIMIT_UP",
    ]
    assert study.market_constraints == list(constraints)


def test_portfolio_study_blocks_limit_down_exit_and_tracks_open_position() -> None:
    bars = [
        _bar(0, open_=10, close=10),
        _bar(1, open_=10, close=10),
        _bar(2, open_=9, high=9, low=9, close=9),
        _bar(3, open_=9, close=8.5),
    ]
    result = _result(
        _signal(SignalSide.BUY, structure=0, confirmed=0, executable=1),
        _signal(SignalSide.SELL, structure=1, confirmed=1, executable=2),
    )

    study = build_portfolio_study(bars, result, _policy())

    assert study.decisions[0].status == "FILLED"
    assert study.decisions[1].reason_code == "PRICE_LIMIT_DOWN"
    assert study.statistics.open_position_quantity == 900
    assert study.statistics.closed_positions == 0
    assert study.statistics.unrealized_pnl == pytest.approx(-1_359)


def test_portfolio_study_explains_holding_state_cash_and_missing_execution() -> None:
    bars = [
        _bar(0, open_=10, close=10),
        _bar(1, open_=10, close=10),
        _bar(2, open_=10, close=10),
    ]
    result = _result(
        _signal(SignalSide.SELL, structure=0, confirmed=0, executable=1),
        _signal(SignalSide.BUY, structure=0, confirmed=0, executable=1),
        _signal(SignalSide.BUY, structure=0, confirmed=1, executable=2),
        _signal(SignalSide.SELL, structure=1, confirmed=2, executable=None),
    )

    study = build_portfolio_study(bars, result, _policy())

    assert [decision.reason_code for decision in study.decisions] == [
        "NO_POSITION",
        "FILLED_NEXT_OPEN",
        "ALREADY_LONG",
        "NO_EXECUTION_BAR",
    ]
    assert study.decisions[-1].status == "NOT_EXECUTABLE"
    assert study.decisions[-1].timing.executable_at is None


def test_portfolio_study_rejects_order_below_one_lot_after_costs() -> None:
    bars = [
        _bar(0, open_=10, close=10),
        _bar(1, open_=10, close=10),
    ]
    result = _result(_signal(SignalSide.BUY, structure=0, confirmed=0, executable=1))

    study = build_portfolio_study(bars, result, _policy(initial_cash=50))

    assert study.decisions[0].reason_code == "INSUFFICIENT_CASH"
    assert study.statistics.filled_orders == 0


def test_portfolio_study_applies_slippage_and_rejects_unobserved_prices() -> None:
    bars = [
        _bar(0, open_=10, close=10),
        _bar(1, open_=10, high=10.02, low=9.9, close=10),
    ]
    result = _result(_signal(SignalSide.BUY, structure=0, confirmed=0, executable=1))

    study = build_portfolio_study(bars, result, _policy(slippage_bps=50))

    assert study.decisions[0].reason_code == "SLIPPAGE_OUTSIDE_BAR"
    assert study.statistics.filled_orders == 0


def test_portfolio_study_does_not_rewrite_prior_decisions_when_bars_extend() -> None:
    prefix = [
        _bar(0, open_=10, close=10),
        _bar(1, open_=10, close=10),
        _bar(2, open_=11, close=11),
    ]
    prefix_result = _result(
        _signal(SignalSide.BUY, structure=0, confirmed=0, executable=1),
        _signal(SignalSide.SELL, structure=1, confirmed=1, executable=2),
    )
    extended = [*prefix, _bar(3, open_=8, close=8)]

    before = build_portfolio_study(prefix, prefix_result, _policy())
    after = build_portfolio_study(extended, prefix_result, _policy())

    assert [decision.model_dump() for decision in before.decisions] == [
        decision.model_dump() for decision in after.decisions
    ]
