from __future__ import annotations

from collections import Counter
from decimal import ROUND_HALF_UP, Decimal

from chan_quant.domain.market import MarketBar, validate_bar_sequence
from chan_quant.domain.portfolio import (
    PortfolioDecision,
    PortfolioEquityPoint,
    PortfolioMarketConstraint,
    PortfolioPolicy,
    PortfolioStatistics,
    PortfolioStudy,
    PortfolioTiming,
    PortfolioWarning,
)
from chan_quant.domain.strategy import SignalSide, StrategyResult, StrategySignal

_BPS = Decimal(10000)


def _decimal(value: float) -> Decimal:
    return Decimal(str(value))


def _money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _price(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def _timing(bars: list[MarketBar], signal: StrategySignal) -> PortfolioTiming:
    executable_at = (
        bars[signal.executable_index].date if signal.executable_index is not None else None
    )
    return PortfolioTiming(
        structure_at=bars[signal.structure_index].date,
        confirmed_at=bars[signal.confirmation_index].date,
        executable_at=executable_at,
    )


def _commission(notional: Decimal, policy: PortfolioPolicy) -> Decimal:
    proportional = notional * _decimal(policy.commission_bps) / _BPS
    return max(proportional, _decimal(policy.minimum_commission))


def _limit_price(previous_close: float, ratio: float, decimals: int, *, upper: bool) -> Decimal:
    multiplier = Decimal(1) + _decimal(ratio) if upper else Decimal(1) - _decimal(ratio)
    quantum = Decimal(1).scaleb(-decimals)
    return (_decimal(previous_close) * multiplier).quantize(quantum, rounding=ROUND_HALF_UP)


def _rejected(
    bars: list[MarketBar],
    signal: StrategySignal,
    reason_code: str,
    *,
    cash: Decimal,
    position: int,
    status: str = "REJECTED",
) -> PortfolioDecision:
    return PortfolioDecision(
        signal_id=signal.id,
        side=signal.side.value,
        status=status,
        reason_code=reason_code,
        timing=_timing(bars, signal),
        cash_after=_money(cash),
        position_after=position,
    )


def _max_buy_quantity(
    cash: Decimal,
    price: Decimal,
    policy: PortfolioPolicy,
) -> tuple[int, Decimal, Decimal]:
    lot_size = policy.lot_size
    budget = cash * _decimal(policy.max_position_fraction)
    quantity = int(budget // (price * lot_size)) * lot_size
    while quantity >= lot_size:
        notional = price * quantity
        commission = _commission(notional, policy)
        if notional + commission <= cash:
            return quantity, notional, commission
        quantity -= lot_size
    return 0, Decimal(0), Decimal(0)


def _max_drawdown(points: list[PortfolioEquityPoint]) -> float:
    peak: float | None = None
    drawdown = 0.0
    for point in points:
        peak = point.equity if peak is None else max(peak, point.equity)
        if peak > 0:
            drawdown = min(drawdown, point.equity / peak - 1)
    return drawdown


def _validate_signal_indexes(bars: list[MarketBar], signals: tuple[StrategySignal, ...]) -> None:
    for signal in signals:
        indexes = (signal.structure_index, signal.confirmation_index)
        if any(index < 0 or index >= len(bars) for index in indexes):
            raise ValueError(f"signal {signal.id} references a bar outside the input")
        if signal.structure_index > signal.confirmation_index:
            raise ValueError(f"signal {signal.id} violates structure <= confirmation")
        if signal.executable_index is not None:
            if signal.executable_index >= len(bars):
                raise ValueError(f"signal {signal.id} executable index is outside the input")
            if signal.confirmation_index >= signal.executable_index:
                raise ValueError(f"signal {signal.id} must execute after confirmation")


def build_portfolio_study(
    bars: list[MarketBar],
    result: StrategyResult,
    policy: PortfolioPolicy | None = None,
    market_constraints: tuple[PortfolioMarketConstraint, ...] = (),
) -> PortfolioStudy:
    """Run a deterministic long-only portfolio study through one small seam.

    The study treats each signal as a one-session next-open intent. It never retries a
    rejected order, never shorts, and never infers actual exchange eligibility from the
    fixed research profile.
    """

    policy = policy or PortfolioPolicy()
    validate_bar_sequence(bars, minimum=2)
    _validate_signal_indexes(bars, result.signals)
    bar_dates = {bar.date for bar in bars}
    if any(item.date not in bar_dates for item in market_constraints):
        raise ValueError("market constraints must reference an input bar date")
    constraints_by_date = {item.date: item for item in market_constraints}
    if len(constraints_by_date) != len(market_constraints):
        raise ValueError("market constraints must have unique dates")

    signals = sorted(result.signals, key=lambda item: item.confirmation_index)
    executable_by_index: dict[int, list[StrategySignal]] = {}
    decisions_by_id: dict[str, PortfolioDecision] = {}
    for signal in signals:
        if signal.executable_index is None:
            continue
        executable_by_index.setdefault(signal.executable_index, []).append(signal)
    if len({signal.id for signal in signals}) != len(signals):
        raise ValueError("signal ids must be unique")

    cash = _decimal(policy.initial_cash)
    position = 0
    entry_total_cost = Decimal(0)
    total_costs = Decimal(0)
    total_slippage = Decimal(0)
    total_notional = Decimal(0)
    realized_pnl = Decimal(0)
    closed_pnls: list[Decimal] = []
    exposure_days = 0
    equity_curve: list[PortfolioEquityPoint] = []

    for index, bar in enumerate(bars):
        for signal in executable_by_index.get(index, []):
            if signal.side is SignalSide.BUY and position:
                decisions_by_id[signal.id] = _rejected(
                    bars, signal, "ALREADY_LONG", cash=cash, position=position
                )
                continue
            if signal.side is SignalSide.SELL and not position:
                decisions_by_id[signal.id] = _rejected(
                    bars, signal, "NO_POSITION", cash=cash, position=position
                )
                continue
            market_constraint = constraints_by_date.get(bar.date)
            if market_constraint is not None and market_constraint.trading_status == "SUSPENDED":
                decisions_by_id[signal.id] = _rejected(
                    bars, signal, "SUSPENDED", cash=cash, position=position
                )
                continue
            if bar.volume == 0:
                decisions_by_id[signal.id] = _rejected(
                    bars, signal, "ZERO_VOLUME", cash=cash, position=position
                )
                continue

            previous_close = bars[index - 1].close
            open_price = _decimal(bar.open)
            if signal.side is SignalSide.BUY:
                upper_limit = (
                    _decimal(market_constraint.upper_limit)
                    if market_constraint is not None and market_constraint.upper_limit is not None
                    else _limit_price(
                        previous_close,
                        policy.price_limit_ratio,
                        policy.price_limit_decimals,
                        upper=True,
                    )
                )
                if open_price >= upper_limit:
                    decisions_by_id[signal.id] = _rejected(
                        bars, signal, "PRICE_LIMIT_UP", cash=cash, position=position
                    )
                    continue
                execution_price = open_price * (Decimal(1) + _decimal(policy.slippage_bps) / _BPS)
                if execution_price > _decimal(bar.high):
                    decisions_by_id[signal.id] = _rejected(
                        bars, signal, "SLIPPAGE_OUTSIDE_BAR", cash=cash, position=position
                    )
                    continue
                quantity, notional, commission = _max_buy_quantity(cash, execution_price, policy)
                if not quantity:
                    decisions_by_id[signal.id] = _rejected(
                        bars, signal, "INSUFFICIENT_CASH", cash=cash, position=position
                    )
                    continue
                slippage_cost = (execution_price - open_price) * quantity
                cash -= notional + commission
                position = quantity
                entry_total_cost = notional + commission
                total_costs += commission
                total_slippage += slippage_cost
                total_notional += notional
                decisions_by_id[signal.id] = PortfolioDecision(
                    signal_id=signal.id,
                    side=signal.side.value,
                    status="FILLED",
                    reason_code="FILLED_NEXT_OPEN",
                    timing=_timing(bars, signal),
                    execution_price=_price(execution_price),
                    quantity=quantity,
                    notional=_money(notional),
                    commission=_money(commission),
                    slippage_cost=_money(slippage_cost),
                    cash_after=_money(cash),
                    position_after=position,
                )
            else:
                lower_limit = (
                    _decimal(market_constraint.lower_limit)
                    if market_constraint is not None and market_constraint.lower_limit is not None
                    else _limit_price(
                        previous_close,
                        policy.price_limit_ratio,
                        policy.price_limit_decimals,
                        upper=False,
                    )
                )
                if open_price <= lower_limit:
                    decisions_by_id[signal.id] = _rejected(
                        bars, signal, "PRICE_LIMIT_DOWN", cash=cash, position=position
                    )
                    continue
                execution_price = open_price * (Decimal(1) - _decimal(policy.slippage_bps) / _BPS)
                if execution_price < _decimal(bar.low):
                    decisions_by_id[signal.id] = _rejected(
                        bars, signal, "SLIPPAGE_OUTSIDE_BAR", cash=cash, position=position
                    )
                    continue
                quantity = position
                notional = execution_price * quantity
                commission = _commission(notional, policy)
                transaction_tax = notional * _decimal(policy.sell_tax_bps) / _BPS
                slippage_cost = (open_price - execution_price) * quantity
                proceeds = notional - commission - transaction_tax
                position_pnl = proceeds - entry_total_cost
                cash += proceeds
                position = 0
                entry_total_cost = Decimal(0)
                total_costs += commission + transaction_tax
                total_slippage += slippage_cost
                total_notional += notional
                realized_pnl += position_pnl
                closed_pnls.append(position_pnl)
                decisions_by_id[signal.id] = PortfolioDecision(
                    signal_id=signal.id,
                    side=signal.side.value,
                    status="FILLED",
                    reason_code="FILLED_NEXT_OPEN",
                    timing=_timing(bars, signal),
                    execution_price=_price(execution_price),
                    quantity=quantity,
                    notional=_money(notional),
                    commission=_money(commission),
                    transaction_tax=_money(transaction_tax),
                    slippage_cost=_money(slippage_cost),
                    cash_after=_money(cash),
                    position_after=position,
                )

        if position:
            exposure_days += 1
        equity = cash + _decimal(bar.close) * position
        equity_curve.append(
            PortfolioEquityPoint(
                date=bar.date,
                cash=_money(cash),
                position_quantity=position,
                close=bar.close,
                equity=_money(equity),
            )
        )

    for signal in signals:
        if signal.executable_index is None:
            decisions_by_id[signal.id] = _rejected(
                bars,
                signal,
                "NO_EXECUTION_BAR",
                cash=cash,
                position=position,
                status="NOT_EXECUTABLE",
            )

    decisions = [decisions_by_id[signal.id] for signal in signals]
    rejected_reasons = Counter(
        decision.reason_code for decision in decisions if decision.status != "FILLED"
    )
    ending_equity = cash + _decimal(bars[-1].close) * position
    unrealized_pnl = (
        _decimal(bars[-1].close) * position - entry_total_cost if position else Decimal(0)
    )
    winning_positions = sum(pnl > 0 for pnl in closed_pnls)
    closed_positions = len(closed_pnls)

    return PortfolioStudy(
        methodology_status="HYPOTHETICAL_RESEARCH_ASSUMPTIONS",
        policy=policy,
        market_constraints=list(market_constraints),
        statistics=PortfolioStatistics(
            starting_cash=policy.initial_cash,
            ending_equity=_money(ending_equity),
            total_return=float(ending_equity / _decimal(policy.initial_cash) - 1),
            max_drawdown=_max_drawdown(equity_curve),
            filled_orders=sum(decision.status == "FILLED" for decision in decisions),
            rejected_orders=sum(decision.status != "FILLED" for decision in decisions),
            rejected_reasons=dict(sorted(rejected_reasons.items())),
            closed_positions=closed_positions,
            winning_positions=winning_positions,
            win_rate=winning_positions / closed_positions if closed_positions else 0,
            total_costs=_money(total_costs),
            slippage_cost=_money(total_slippage),
            turnover=float(total_notional / _decimal(policy.initial_cash)),
            exposure_ratio=exposure_days / len(bars),
            open_position_quantity=position,
            realized_pnl=_money(realized_pnl),
            unrealized_pnl=_money(unrealized_pnl),
        ),
        decisions=decisions,
        equity_curve=equity_curve,
        warnings=[
            PortfolioWarning(
                code="FIXED_LIMIT_ASSUMPTION",
                message=(
                    "固定 10% 涨跌停与两位价格舍入只是研究假设，不覆盖 ST、"
                    "20%/30%、IPO、ETF、指数及规则变更。"
                ),
            ),
            PortfolioWarning(
                code="MARKET_STATUS_NOT_OBSERVED",
                message=(
                    "未提供逐日外部状态时，模型不知道证券是否正式停牌；零成交量会"
                    "阻止假设成交，但不能单独证明停牌。"
                ),
            ),
            PortfolioWarning(
                code="DAILY_BAR_EXECUTION_LIMIT",
                message=(
                    "日 K 只能约束开高低收范围，不能证明涨跌停排队、盘中流动性、"
                    "订单规模或真实成交优先级。"
                ),
            ),
        ],
    )
