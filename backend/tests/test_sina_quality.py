from datetime import date, timedelta
from pathlib import Path

import pytest

from chan_quant.audit.sina_quality import (
    ReferenceDailyBar,
    audit_sina_quality,
    compare_sina_snapshots,
    load_open_dates_csv,
    load_reference_daily_csv,
)
from chan_quant.domain.market import MarketBar


def _candidate(index: int, close: float, *, volume: int = 10_000) -> MarketBar:
    return MarketBar(
        date=date(2026, 6, 10) + timedelta(days=index),
        open=close - 0.1,
        high=close + 0.2,
        low=close - 0.2,
        close=close,
        volume=volume,
    )


def _reference(
    index: int,
    close: float,
    *,
    pre_close: float,
    volume: float = 100.0,
) -> ReferenceDailyBar:
    return ReferenceDailyBar(
        date=date(2026, 6, 10) + timedelta(days=index),
        open=close - 0.1,
        high=close + 0.2,
        low=close - 0.2,
        close=close,
        pre_close=pre_close,
        volume=volume,
    )


def test_audit_classifies_raw_prices_only_with_corporate_action_evidence() -> None:
    candidates = [_candidate(0, 11.3), _candidate(1, 11.24), _candidate(2, 11.06)]
    references = [
        _reference(0, 11.3, pre_close=11.2),
        _reference(1, 11.24, pre_close=10.94),
        _reference(2, 11.06, pre_close=11.24),
    ]

    report = audit_sina_quality("000001.SZ", candidates, references)

    assert report.adjustment_classification == "unadjusted_observed"
    assert report.raw_price_match_ratio == 1.0
    assert report.volume_unit_ratio_median == 100.0
    assert report.corporate_action_events[0].date == date(2026, 6, 11)
    assert report.corporate_action_events[0].candidate_matches_reference_raw is True


def test_audit_keeps_unknown_when_prices_do_not_match_raw_reference() -> None:
    candidates = [_candidate(0, 10.94), _candidate(1, 11.24)]
    references = [
        _reference(0, 11.3, pre_close=11.2),
        _reference(1, 11.24, pre_close=10.94),
    ]

    report = audit_sina_quality("000001.SZ", candidates, references)

    assert report.adjustment_classification == "insufficient_evidence"
    assert report.price_mismatch_dates == (date(2026, 6, 10),)


def test_audit_separates_reference_gaps_from_open_day_gaps() -> None:
    candidates = [_candidate(0, 10), _candidate(2, 12), _candidate(4, 14)]
    references = [
        _reference(0, 10, pre_close=9.9),
        _reference(1, 11, pre_close=10),
        _reference(2, 12, pre_close=11),
        _reference(4, 14, pre_close=13),
    ]
    open_dates = {date(2026, 6, 10) + timedelta(days=index) for index in range(5)}

    report = audit_sina_quality(
        "000001.SZ", candidates, references, open_dates=open_dates
    )

    assert report.missing_reference_dates == (date(2026, 6, 11),)
    assert report.open_dates_without_candidate == (
        date(2026, 6, 11),
        date(2026, 6, 13),
    )
    assert report.open_dates_without_reference == (date(2026, 6, 13),)


def test_snapshot_comparison_reports_historical_revisions() -> None:
    previous = [_candidate(0, 10), _candidate(1, 11)]
    current = [_candidate(0, 10.5), _candidate(1, 11), _candidate(2, 12)]

    report = compare_sina_snapshots(previous, current)

    assert report.overlapping_rows == 2
    assert report.revisions[0].date == date(2026, 6, 10)
    assert report.revisions[0].fields == ("open", "high", "low", "close")
    assert report.added_dates == (date(2026, 6, 12),)


def test_snapshot_comparison_rejects_invalid_audit_inputs() -> None:
    duplicate = [_candidate(0, 10), _candidate(0, 10)]

    with pytest.raises(
        ValueError,
        match="previous snapshot must not contain duplicate dates",
    ):
        compare_sina_snapshots(duplicate, [])
    with pytest.raises(ValueError, match="price_tolerance must be positive"):
        compare_sina_snapshots([], [], price_tolerance=0)


def test_reference_csv_loader_accepts_tushare_and_iso_aliases(tmp_path: Path) -> None:
    tushare = tmp_path / "tushare.csv"
    tushare.write_text(
        "trade_date,open,high,low,close,pre_close,vol\n"
        "20260612,11.00,11.25,10.88,11.24,10.94,123.5\n",
        encoding="utf-8",
    )
    generic = tmp_path / "generic.csv"
    generic.write_text(
        "date,open,high,low,close,pre_close,volume\n"
        "2026-06-12,11.00,11.25,10.88,11.24,10.94,123.5\n",
        encoding="utf-8",
    )

    expected = ReferenceDailyBar(
        date=date(2026, 6, 12),
        open=11.0,
        high=11.25,
        low=10.88,
        close=11.24,
        pre_close=10.94,
        volume=123.5,
    )
    assert load_reference_daily_csv(tushare) == [expected]
    assert load_reference_daily_csv(generic) == [expected]


def test_reference_csv_loader_rejects_missing_columns(tmp_path: Path) -> None:
    source = tmp_path / "missing.csv"
    source.write_text(
        "trade_date,open,high,low,close,vol\n"
        "20260612,11.00,11.25,10.88,11.24,123.5\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="reference CSV is missing fields: pre_close",
    ):
        load_reference_daily_csv(source)


def test_calendar_csv_loader_keeps_only_open_dates(tmp_path: Path) -> None:
    source = tmp_path / "calendar.csv"
    source.write_text(
        "cal_date,is_open\n"
        "20260612,1\n"
        "2026-06-13,0\n"
        "2026-06-16, 1 \n",
        encoding="utf-8",
    )

    assert load_open_dates_csv(source) == {
        date(2026, 6, 12),
        date(2026, 6, 16),
    }


def test_calendar_csv_loader_rejects_missing_columns(tmp_path: Path) -> None:
    source = tmp_path / "calendar.csv"
    source.write_text("cal_date\n20260612\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="calendar CSV requires cal_date and is_open",
    ):
        load_open_dates_csv(source)
