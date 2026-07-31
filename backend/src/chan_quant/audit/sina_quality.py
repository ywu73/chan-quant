from __future__ import annotations

import argparse
import csv
import json
import statistics
from dataclasses import asdict, dataclass
from datetime import date
from itertools import pairwise
from pathlib import Path

from chan_quant.data.sina_source import fetch_sina_kline_bars
from chan_quant.domain.market import MarketBar


@dataclass(frozen=True, slots=True)
class ReferenceDailyBar:
    date: date
    open: float
    high: float
    low: float
    close: float
    pre_close: float
    volume: float


@dataclass(frozen=True, slots=True)
class CorporateActionEvidence:
    date: date
    previous_date: date
    previous_raw_close: float
    adjusted_pre_close: float
    candidate_matches_reference_raw: bool


@dataclass(frozen=True, slots=True)
class SinaQualityReport:
    symbol: str
    reference_start: date
    reference_end: date
    candidate_rows_in_window: int
    reference_rows: int
    matched_rows: int
    raw_price_match_ratio: float
    price_mismatch_dates: tuple[date, ...]
    volume_mismatch_dates: tuple[date, ...]
    volume_unit_ratio_median: float | None
    missing_reference_dates: tuple[date, ...]
    extra_candidate_dates: tuple[date, ...]
    open_dates_without_candidate: tuple[date, ...]
    open_dates_without_reference: tuple[date, ...]
    corporate_action_events: tuple[CorporateActionEvidence, ...]
    adjustment_classification: str


@dataclass(frozen=True, slots=True)
class SnapshotRevision:
    date: date
    fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SnapshotStabilityReport:
    overlapping_rows: int
    revisions: tuple[SnapshotRevision, ...]
    added_dates: tuple[date, ...]
    removed_dates: tuple[date, ...]


def _parse_date(raw: str) -> date:
    value = raw.strip()
    if len(value) == 8 and value.isdigit():
        return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
    return date.fromisoformat(value)


def _prices_match(
    candidate: MarketBar,
    reference: ReferenceDailyBar,
    *,
    tolerance: float,
) -> bool:
    return all(
        abs(left - right) <= tolerance
        for left, right in (
            (candidate.open, reference.open),
            (candidate.high, reference.high),
            (candidate.low, reference.low),
            (candidate.close, reference.close),
        )
    )


def audit_sina_quality(
    symbol: str,
    candidate_bars: list[MarketBar],
    reference_bars: list[ReferenceDailyBar],
    *,
    open_dates: set[date] | None = None,
    price_tolerance: float = 0.011,
    reference_volume_multiplier: float = 100.0,
) -> SinaQualityReport:
    if not reference_bars:
        raise ValueError("reference_bars must not be empty")
    if price_tolerance <= 0:
        raise ValueError("price_tolerance must be positive")
    if reference_volume_multiplier <= 0:
        raise ValueError("reference_volume_multiplier must be positive")

    reference_sorted = sorted(reference_bars, key=lambda item: item.date)
    reference_by_date = {item.date: item for item in reference_sorted}
    if len(reference_by_date) != len(reference_sorted):
        raise ValueError("reference_bars must not contain duplicate dates")

    reference_start = reference_sorted[0].date
    reference_end = reference_sorted[-1].date
    candidate_window = [
        item for item in candidate_bars if reference_start <= item.date <= reference_end
    ]
    candidate_by_date = {item.date: item for item in candidate_window}
    if len(candidate_by_date) != len(candidate_window):
        raise ValueError("candidate_bars must not contain duplicate dates")

    common_dates = sorted(candidate_by_date.keys() & reference_by_date.keys())
    price_mismatches = [
        trade_date
        for trade_date in common_dates
        if not _prices_match(
            candidate_by_date[trade_date],
            reference_by_date[trade_date],
            tolerance=price_tolerance,
        )
    ]

    volume_ratios: list[float] = []
    volume_mismatches: list[date] = []
    for trade_date in common_dates:
        candidate_volume = candidate_by_date[trade_date].volume
        reference_volume = reference_by_date[trade_date].volume
        if reference_volume > 0:
            volume_ratios.append(candidate_volume / reference_volume)
        expected = reference_volume * reference_volume_multiplier
        if abs(candidate_volume - expected) > max(1.0, expected * 1e-6):
            volume_mismatches.append(trade_date)

    action_events: list[CorporateActionEvidence] = []
    for previous, current in pairwise(reference_sorted):
        if abs(current.pre_close - previous.close) <= price_tolerance:
            continue
        candidate_previous = candidate_by_date.get(previous.date)
        candidate_current = candidate_by_date.get(current.date)
        raw_match = (
            candidate_previous is not None
            and candidate_current is not None
            and abs(candidate_previous.close - previous.close) <= price_tolerance
            and _prices_match(
                candidate_current,
                current,
                tolerance=price_tolerance,
            )
        )
        action_events.append(
            CorporateActionEvidence(
                date=current.date,
                previous_date=previous.date,
                previous_raw_close=previous.close,
                adjusted_pre_close=current.pre_close,
                candidate_matches_reference_raw=raw_match,
            )
        )

    raw_match_ratio = (
        (len(common_dates) - len(price_mismatches)) / len(common_dates)
        if common_dates
        else 0.0
    )
    if (
        action_events
        and all(item.candidate_matches_reference_raw for item in action_events)
        and raw_match_ratio >= 0.99
    ):
        adjustment_classification = "unadjusted_observed"
    else:
        adjustment_classification = "insufficient_evidence"

    reference_dates = set(reference_by_date)
    candidate_dates = set(candidate_by_date)
    calendar_window = {
        item
        for item in (open_dates or set())
        if reference_start <= item <= reference_end
    }
    return SinaQualityReport(
        symbol=symbol.upper(),
        reference_start=reference_start,
        reference_end=reference_end,
        candidate_rows_in_window=len(candidate_window),
        reference_rows=len(reference_sorted),
        matched_rows=len(common_dates),
        raw_price_match_ratio=raw_match_ratio,
        price_mismatch_dates=tuple(price_mismatches),
        volume_mismatch_dates=tuple(volume_mismatches),
        volume_unit_ratio_median=(
            statistics.median(volume_ratios) if volume_ratios else None
        ),
        missing_reference_dates=tuple(sorted(reference_dates - candidate_dates)),
        extra_candidate_dates=tuple(sorted(candidate_dates - reference_dates)),
        open_dates_without_candidate=tuple(sorted(calendar_window - candidate_dates)),
        open_dates_without_reference=tuple(sorted(calendar_window - reference_dates)),
        corporate_action_events=tuple(action_events),
        adjustment_classification=adjustment_classification,
    )


def compare_sina_snapshots(
    previous: list[MarketBar],
    current: list[MarketBar],
    *,
    price_tolerance: float = 0.0001,
) -> SnapshotStabilityReport:
    if price_tolerance <= 0:
        raise ValueError("price_tolerance must be positive")
    previous_by_date = {item.date: item for item in previous}
    current_by_date = {item.date: item for item in current}
    if len(previous_by_date) != len(previous):
        raise ValueError("previous snapshot must not contain duplicate dates")
    if len(current_by_date) != len(current):
        raise ValueError("current snapshot must not contain duplicate dates")
    revisions: list[SnapshotRevision] = []
    for trade_date in sorted(previous_by_date.keys() & current_by_date.keys()):
        left = previous_by_date[trade_date]
        right = current_by_date[trade_date]
        changed = []
        for field in ("open", "high", "low", "close"):
            if abs(getattr(left, field) - getattr(right, field)) > price_tolerance:
                changed.append(field)
        if left.volume != right.volume:
            changed.append("volume")
        if changed:
            revisions.append(SnapshotRevision(date=trade_date, fields=tuple(changed)))
    return SnapshotStabilityReport(
        overlapping_rows=len(previous_by_date.keys() & current_by_date.keys()),
        revisions=tuple(revisions),
        added_dates=tuple(sorted(current_by_date.keys() - previous_by_date.keys())),
        removed_dates=tuple(sorted(previous_by_date.keys() - current_by_date.keys())),
    )


def load_reference_daily_csv(path: str | Path) -> list[ReferenceDailyBar]:
    rows: list[ReferenceDailyBar] = []
    with Path(path).expanduser().open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        date_field = "trade_date" if "trade_date" in fields else "date"
        volume_field = "vol" if "vol" in fields else "volume"
        required = {
            date_field,
            "open",
            "high",
            "low",
            "close",
            "pre_close",
            volume_field,
        }
        missing = required - fields
        if missing:
            raise ValueError(f"reference CSV is missing fields: {', '.join(sorted(missing))}")
        for row in reader:
            rows.append(
                ReferenceDailyBar(
                    date=_parse_date(row[date_field]),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    pre_close=float(row["pre_close"]),
                    volume=float(row[volume_field]),
                )
            )
    return rows


def load_open_dates_csv(path: str | Path) -> set[date]:
    dates: set[date] = set()
    with Path(path).expanduser().open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        if not {"cal_date", "is_open"} <= fields:
            raise ValueError("calendar CSV requires cal_date and is_open")
        for row in reader:
            if str(row["is_open"]).strip() == "1":
                dates.add(_parse_date(row["cal_date"]))
    return dates


def _json_default(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    raise TypeError(f"cannot serialize {type(value).__name__}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Sina daily K-line data quality")
    parser.add_argument("--symbol", required=True, help="Canonical symbol, e.g. 000001.SZ")
    parser.add_argument("--reference-daily", required=True, help="Reference raw daily CSV")
    parser.add_argument("--calendar", help="Optional exchange calendar CSV")
    parser.add_argument("--datalen", type=int, default=2_000)
    parser.add_argument("--reference-volume-multiplier", type=float, default=100.0)
    args = parser.parse_args()

    candidate = fetch_sina_kline_bars(args.symbol, datalen=args.datalen)
    reference = load_reference_daily_csv(args.reference_daily)
    calendar = load_open_dates_csv(args.calendar) if args.calendar else None
    report = audit_sina_quality(
        args.symbol,
        candidate,
        reference,
        open_dates=calendar,
        reference_volume_multiplier=args.reference_volume_multiplier,
    )
    print(json.dumps(asdict(report), ensure_ascii=False, indent=2, default=_json_default))


if __name__ == "__main__":
    main()
