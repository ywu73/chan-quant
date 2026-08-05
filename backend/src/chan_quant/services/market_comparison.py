from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date

from chan_quant.domain.comparison import (
    ComparisonAlignment,
    ComparisonFailure,
    ComparisonSeries,
    ComparisonWarning,
    MarketComparison,
)
from chan_quant.domain.instrument import InstrumentIdentity
from chan_quant.domain.market import MarketBar, validate_bar_sequence


@dataclass(frozen=True, slots=True)
class ComparisonInput:
    instrument: InstrumentIdentity
    bars: list[MarketBar]
    data_source: str
    adjustment: str
    is_mock: bool
    warnings: list[ComparisonWarning]


class ComparisonLoadError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class _LoadedSeries:
    source: ComparisonInput
    bars: list[MarketBar]


def _failure(symbol: str, code: str, message: str) -> ComparisonFailure:
    return ComparisonFailure(symbol=symbol, code=code, message=message)


def _drawdown(
    bars: list[MarketBar],
) -> tuple[float, date | None, date | None]:
    peak_price = bars[0].close
    peak_at = bars[0].date
    max_drawdown = 0.0
    max_peak_at: date | None = None
    max_trough_at: date | None = None

    for bar in bars[1:]:
        if bar.close > peak_price:
            peak_price = bar.close
            peak_at = bar.date
            continue
        drawdown = bar.close / peak_price - 1
        if drawdown < max_drawdown:
            max_drawdown = drawdown
            max_peak_at = peak_at
            max_trough_at = bar.date

    return max_drawdown, max_peak_at, max_trough_at


def _load_one(
    symbol: str,
    loader: Callable[[str], ComparisonInput],
    start: date | None,
    end: date | None,
) -> _LoadedSeries | ComparisonFailure:
    try:
        source = loader(symbol)
    except ComparisonLoadError as error:
        return _failure(symbol, error.code, error.message)

    bars = [
        bar
        for bar in source.bars
        if (start is None or bar.date >= start) and (end is None or bar.date <= end)
    ]
    try:
        validate_bar_sequence(bars, minimum=2)
    except ValueError as error:
        return _failure(symbol, "INSUFFICIENT_DATA", str(error))
    return _LoadedSeries(source=source, bars=bars)


def _load_requested(
    symbols: list[str],
    loader: Callable[[str], ComparisonInput],
    start: date | None,
    end: date | None,
    max_workers: int,
) -> tuple[list[_LoadedSeries], list[ComparisonFailure]]:
    if max_workers == 1 or len(symbols) <= 1:
        outcomes = [_load_one(symbol, loader, start, end) for symbol in symbols]
    else:
        with ThreadPoolExecutor(max_workers=min(max_workers, len(symbols))) as executor:
            futures = [
                executor.submit(_load_one, symbol, loader, start, end) for symbol in symbols
            ]
            outcomes = [future.result() for future in futures]

    loaded = [outcome for outcome in outcomes if isinstance(outcome, _LoadedSeries)]
    failures = [outcome for outcome in outcomes if isinstance(outcome, ComparisonFailure)]
    return loaded, failures


def _align_common_window(
    loaded: list[_LoadedSeries],
    failures: list[ComparisonFailure],
) -> tuple[list[_LoadedSeries], date | None, date | None]:
    active = loaded
    while active:
        common_from = max(item.bars[0].date for item in active)
        common_to = min(item.bars[-1].date for item in active)
        if common_from > common_to:
            failures.extend(
                _failure(
                    item.source.instrument.symbol,
                    "NO_OVERLAPPING_RANGE",
                    "series has no overlapping date range with the other requested instruments",
                )
                for item in active
            )
            return [], None, None

        retained: list[_LoadedSeries] = []
        removed = False
        for item in active:
            bars = [bar for bar in item.bars if common_from <= bar.date <= common_to]
            if len(bars) < 2:
                failures.append(
                    _failure(
                        item.source.instrument.symbol,
                        "INSUFFICIENT_COMMON_DATA",
                        "series has fewer than two observations in the common date range",
                    )
                )
                removed = True
            else:
                retained.append(_LoadedSeries(source=item.source, bars=bars))
        active = retained
        if not removed:
            return active, common_from, common_to
    return [], None, None


def _build_series(item: _LoadedSeries, dates: list[date]) -> ComparisonSeries:
    baseline = item.bars[0]
    final = item.bars[-1]
    previous_trading_day_return = (
        item.bars[-2].close / item.bars[-3].close - 1 if len(item.bars) >= 3 else None
    )
    normalized_by_date = {bar.date: bar.close / baseline.close - 1 for bar in item.bars}
    max_drawdown, peak_at, trough_at = _drawdown(item.bars)
    return ComparisonSeries(
        instrument=item.source.instrument,
        data_source=item.source.data_source,
        adjustment=item.source.adjustment,
        currency=item.source.instrument.currency,
        is_mock=item.source.is_mock,
        data_from=item.bars[0].date,
        data_to=item.bars[-1].date,
        baseline_at=baseline.date,
        baseline_price=baseline.close,
        latest_close=final.close,
        previous_trading_day_return=previous_trading_day_return,
        values=[normalized_by_date.get(day) for day in dates],
        cumulative_return=final.close / baseline.close - 1,
        max_drawdown=max_drawdown,
        max_drawdown_peak_at=peak_at,
        max_drawdown_trough_at=trough_at,
        coverage_ratio=len(item.bars) / len(dates),
        warnings=item.source.warnings,
    )


def build_market_comparison(
    symbols: list[str],
    loader: Callable[[str], ComparisonInput],
    *,
    start: date | None = None,
    end: date | None = None,
    max_workers: int = 1,
) -> MarketComparison:
    """Load, align, and calculate a comparison through one auditable seam."""
    if start is not None and end is not None and start > end:
        raise ValueError("comparison start date must not be after end date")
    if max_workers <= 0:
        raise ValueError("comparison max_workers must be positive")

    loaded, failures = _load_requested(symbols, loader, start, end, max_workers)
    aligned, common_from, common_to = _align_common_window(loaded, failures)
    dates = sorted({bar.date for item in aligned for bar in item.bars})
    series = [_build_series(item, dates) for item in aligned]

    warnings: list[ComparisonWarning] = []
    currencies = {item.instrument.currency for item in series}
    timezones = {item.instrument.timezone for item in series}
    if len(currencies) > 1:
        warnings.append(
            ComparisonWarning(
                code="NATIVE_CURRENCY_NO_FX_CONVERSION",
                message=(
                    "各标的保留原始计价币种；归一化收益不进行汇率换算，"
                    "因此不能解释为同一基准货币下的投资回报。"
                ),
            )
        )
    if len(timezones) > 1:
        warnings.append(
            ComparisonWarning(
                code="LOCAL_TRADING_DATE_ALIGNMENT",
                message=(
                    "日期按各标的 IANA 时区下的本地常规交易时段收盘对齐；"
                    "同一 ISO 日期不代表同一时刻，盘前盘后行情不纳入比较。"
                ),
            )
        )

    status = "COMPLETE" if not failures else "PARTIAL" if series else "FAILED"
    return MarketComparison(
        status=status,
        requested=symbols,
        succeeded=len(series),
        failed=len(failures),
        requested_from=start,
        requested_to=end,
        common_from=common_from,
        common_to=common_to,
        dates=dates,
        alignment=ComparisonAlignment(),
        warnings=warnings,
        series=series,
        failures=failures,
    )
