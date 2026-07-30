from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from chan_quant.domain.market import MarketBar, validate_bar_sequence


class CsvDataError(ValueError):
    """Raised when a CSV file violates the normalized market-data contract."""


def _parse_date(raw: str) -> date:
    value = raw.strip()
    try:
        return date.fromisoformat(value)
    except ValueError:
        pass
    if len(value) == 8 and value.isdigit():
        try:
            return date(int(value[:4]), int(value[4:6]), int(value[6:8]))
        except ValueError:
            pass
    raise CsvDataError(f"unsupported trade date: {raw!r}")


def load_csv_bars(path: str | Path) -> list[MarketBar]:
    csv_path = Path(path).expanduser()
    if not csv_path.is_file():
        raise CsvDataError(f"CSV file does not exist: {csv_path}")

    bars: list[MarketBar] = []
    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = set(reader.fieldnames or [])
            date_field = "trade_date" if "trade_date" in fieldnames else "date"
            required = {date_field, "open", "high", "low", "close", "volume"}
            missing = required - fieldnames
            if missing:
                raise CsvDataError(f"CSV is missing fields: {', '.join(sorted(missing))}")

            for row_number, row in enumerate(reader, start=2):
                try:
                    amount_raw = (row.get("amount") or "").strip()
                    bars.append(
                        MarketBar(
                            date=_parse_date(row[date_field]),
                            open=float(row["open"]),
                            high=float(row["high"]),
                            low=float(row["low"]),
                            close=float(row["close"]),
                            volume=int(float(row["volume"])),
                            amount=float(amount_raw) if amount_raw else None,
                        )
                    )
                except (KeyError, TypeError, ValueError) as error:
                    if isinstance(error, CsvDataError):
                        raise
                    raise CsvDataError(f"invalid row {row_number}: {error}") from error
    except UnicodeDecodeError as error:
        raise CsvDataError("CSV must be UTF-8 or UTF-8 with BOM") from error

    bars.sort(key=lambda item: item.date)
    try:
        validate_bar_sequence(bars)
    except ValueError as error:
        raise CsvDataError(str(error)) from error
    return bars
