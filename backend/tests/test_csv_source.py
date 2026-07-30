from pathlib import Path

import pytest

from chan_quant.data.csv_source import CsvDataError, load_csv_bars


def test_csv_source_normalizes_date_order(tmp_path: Path) -> None:
    source = tmp_path / "bars.csv"
    source.write_text(
        "trade_date,open,high,low,close,volume,amount\n"
        "20260103,10,12,9,11,2000,22000\n"
        "2026-01-02,9,11,8,10,1000,10000\n",
        encoding="utf-8",
    )
    bars = load_csv_bars(source)
    assert [bar.date.isoformat() for bar in bars] == ["2026-01-02", "2026-01-03"]
    assert bars[0].volume == 1000
    assert bars[1].amount == 22000


def test_csv_source_rejects_duplicate_dates(tmp_path: Path) -> None:
    source = tmp_path / "bars.csv"
    source.write_text(
        "date,open,high,low,close,volume\n2026-01-02,9,11,8,10,1000\n2026-01-02,10,12,9,11,2000\n",
        encoding="utf-8",
    )
    with pytest.raises(CsvDataError, match="duplicate"):
        load_csv_bars(source)
