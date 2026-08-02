from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import httpx
from pydantic import ValidationError

from chan_quant.data.market_breadth_package import (
    MarketBreadthPackageError,
    load_market_breadth_package,
)
from chan_quant.data.sina_market_breadth_source import (
    SinaMarketBreadthSourceError,
    fetch_sina_market_breadth,
)
from chan_quant.data.sina_source import SinaDataError, to_sina_symbol
from chan_quant.domain.market_breadth import (
    BreadthObservation,
    BreadthUniverseMember,
    MarketBreadthSnapshot,
)

_UNIVERSE_FIELDS = [
    "symbol",
    "exchange",
    "security_name",
    "security_type",
    "board",
    "list_date",
    "delist_date",
]
_QUOTE_FIELDS = [
    "symbol",
    "session_date",
    "previous_close",
    "last_price",
    "unavailable_reason",
    "provider_change_percent",
]


class SinaMarketBreadthImportError(ValueError):
    """Raised when a Sina import cannot publish an accepted package."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class SinaMarketBreadthImportReceipt:
    package_path: Path
    snapshot: MarketBreadthSnapshot


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _universe_rows(members: Sequence[BreadthUniverseMember]) -> list[dict[str, str]]:
    return [
        {
            "symbol": item.symbol,
            "exchange": item.exchange,
            "security_name": item.security_name,
            "security_type": item.security_type,
            "board": item.board,
            "list_date": item.list_date.isoformat(),
            "delist_date": item.delist_date.isoformat() if item.delist_date else "",
        }
        for item in members
    ]


def _quote_rows(observations: Sequence[BreadthObservation]) -> list[dict[str, str]]:
    return [
        {
            "symbol": item.symbol,
            "session_date": item.session_date.isoformat(),
            "previous_close": str(item.previous_close) if item.previous_close is not None else "",
            "last_price": str(item.last_price) if item.last_price is not None else "",
            "unavailable_reason": item.unavailable_reason or "",
            "provider_change_percent": (
                str(item.provider_change_percent)
                if item.provider_change_percent is not None
                else ""
            ),
        }
        for item in observations
    ]


def _load_universe_csv(path: Path, *, session_date: date) -> list[BreadthUniverseMember]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != _UNIVERSE_FIELDS:
                raise SinaMarketBreadthImportError(
                    "SINA_BREADTH_UNIVERSE_CONTRACT_INVALID",
                    f"expected CSV header {','.join(_UNIVERSE_FIELDS)}",
                )
            rows = list(reader)
    except UnicodeDecodeError as error:
        raise SinaMarketBreadthImportError(
            "SINA_BREADTH_UNIVERSE_CONTRACT_INVALID",
            "universe CSV must be UTF-8",
        ) from error
    except (OSError, csv.Error) as error:
        raise SinaMarketBreadthImportError(
            "SINA_BREADTH_UNIVERSE_READ_FAILED",
            str(error),
        ) from error

    members: list[BreadthUniverseMember] = []
    for row_number, row in enumerate(rows, start=2):
        if None in row or any(value is None for value in row.values()):
            raise SinaMarketBreadthImportError(
                "SINA_BREADTH_UNIVERSE_CONTRACT_INVALID",
                f"malformed universe row {row_number}",
            )
        try:
            list_date = date.fromisoformat(row["list_date"].strip())
            delist_date = (
                date.fromisoformat(row["delist_date"].strip())
                if row["delist_date"].strip()
                else None
            )
            member = BreadthUniverseMember(
                symbol=row["symbol"].strip().upper(),
                exchange=row["exchange"].strip().upper(),
                security_name=row["security_name"].strip(),
                security_type=row["security_type"].strip().upper(),
                board=row["board"].strip().upper(),
                list_date=list_date,
                delist_date=delist_date,
            )
        except (ValueError, ValidationError) as error:
            raise SinaMarketBreadthImportError(
                "SINA_BREADTH_UNIVERSE_CONTRACT_INVALID",
                f"row {row_number}: {error}",
            ) from error
        if member.list_date > session_date or (
            member.delist_date is not None and member.delist_date <= session_date
        ):
            raise SinaMarketBreadthImportError(
                "SINA_BREADTH_UNIVERSE_MEMBER_OUTSIDE_SESSION",
                f"{member.symbol} was not listed for session {session_date}",
            )
        members.append(member)
    return members


def generate_sina_market_breadth_package(
    *,
    universe_members: Sequence[BreadthUniverseMember],
    universe_id: str,
    universe_source: str,
    license_note: str,
    inclusion_rules: list[str],
    exclusion_rules: list[str],
    session_date: date,
    output_root: str | Path,
    acknowledge_undocumented_source: bool,
    batch_size: int,
    max_capture_seconds: int = 60,
    client: httpx.Client | None = None,
    clock: Callable[[], datetime] | None = None,
) -> SinaMarketBreadthImportReceipt:
    if not acknowledge_undocumented_source:
        raise SinaMarketBreadthImportError(
            "SINA_BREADTH_NOT_ACKNOWLEDGED",
            "explicit acknowledgement of the undocumented Sina source is required",
        )
    if not universe_members:
        raise SinaMarketBreadthImportError(
            "SINA_BREADTH_UNIVERSE_EMPTY",
            "official Shanghai/Shenzhen universe must not be empty",
        )
    if max_capture_seconds <= 0:
        raise SinaMarketBreadthImportError(
            "SINA_BREADTH_CAPTURE_WINDOW_INVALID",
            "maximum capture window must be positive",
        )
    symbols = [member.symbol for member in universe_members]
    if len(symbols) != len(set(symbols)):
        raise SinaMarketBreadthImportError(
            "SINA_BREADTH_DUPLICATE_SYMBOL",
            "official universe contains duplicate symbols",
        )
    try:
        for member in universe_members:
            to_sina_symbol(member.symbol)
            if member.symbol.rsplit(".", 1)[-1] != member.exchange:
                raise SinaDataError("symbol suffix does not match exchange")
    except SinaDataError as error:
        raise SinaMarketBreadthImportError(
            "SINA_BREADTH_IDENTITY_INVALID",
            str(error),
        ) from error

    try:
        capture = fetch_sina_market_breadth(
            symbols,
            session_date=session_date,
            batch_size=batch_size,
            client=client,
            clock=clock,
        )
    except SinaMarketBreadthSourceError as error:
        raise SinaMarketBreadthImportError(error.code, error.message) from error
    capture_seconds = (capture.completed_at - capture.started_at).total_seconds()
    if capture_seconds > max_capture_seconds:
        raise SinaMarketBreadthImportError(
            "SINA_BREADTH_CAPTURE_WINDOW_EXCEEDED",
            f"capture window {capture_seconds:.3f}s exceeds {max_capture_seconds}s",
        )
    root = Path(output_root).expanduser()
    packages_root = root / "packages"
    packages_root.mkdir(parents=True, exist_ok=True)
    temporary = packages_root / f".tmp-{uuid.uuid4().hex}"
    temporary.mkdir()
    current_temporary: Path | None = None
    try:
        evidence_dir = temporary / "evidence"
        evidence_dir.mkdir()
        evidence_files: list[dict[str, object]] = []
        for batch in capture.raw_batches:
            relative = f"evidence/sina-quotes-batch-{batch.index:04d}.txt"
            evidence_path = temporary / relative
            evidence_path.write_bytes(batch.content)
            evidence_files.append(
                {
                    "path": relative,
                    "bytes": evidence_path.stat().st_size,
                    "sha256": _hash(evidence_path),
                }
            )

        universe_path = temporary / "universe.csv"
        quotes_path = temporary / "quotes.csv"
        _write_csv(universe_path, _UNIVERSE_FIELDS, _universe_rows(universe_members))
        _write_csv(quotes_path, _QUOTE_FIELDS, _quote_rows(capture.observations))
        manifest = {
            "schema_version": "market-breadth-package-v0.2",
            "market": "CN_A_SH_SZ_V1",
            "mode": "EOD",
            "timezone": "Asia/Shanghai",
            "session_date": session_date.isoformat(),
            "universe_id": universe_id,
            "universe_as_of": session_date.isoformat(),
            "fetched_at": capture.completed_at.isoformat(),
            "source": "sina-undocumented-eod-import",
            "universe_source": universe_source,
            "quote_source": "sina-hq-undocumented",
            "license_note": license_note,
            "inclusion_rules": inclusion_rules,
            "exclusion_rules": exclusion_rules,
            "universe_row_count": len(universe_members),
            "quotes_row_count": len(capture.observations),
            "universe_bytes": universe_path.stat().st_size,
            "quotes_bytes": quotes_path.stat().st_size,
            "universe_sha256": _hash(universe_path),
            "quotes_sha256": _hash(quotes_path),
            "quality_policy_version": "market-breadth-quality-v0.1",
            "calculation_policy_version": "market-breadth-calculation-v0.1",
            "session_date_evidence": "provider-row-date",
            "snapshot_started_at": capture.started_at.isoformat(),
            "snapshot_completed_at": capture.completed_at.isoformat(),
            "quote_contract": "sina-hq-undocumented-observed-v0.1",
            "request_batch_size": capture.batch_size,
            "request_count": capture.request_count,
            "evidence_files": evidence_files,
        }
        (temporary / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        try:
            snapshot = load_market_breadth_package(temporary)
        except MarketBreadthPackageError as error:
            raise SinaMarketBreadthImportError(
                "SINA_BREADTH_PACKAGE_VALIDATION_FAILED",
                f"{error.code}: {error.message}",
            ) from error
        if snapshot.status == "FAILED":
            raise SinaMarketBreadthImportError(
                "SINA_BREADTH_INSUFFICIENT_RESOLUTION",
                "generated package did not meet the market breadth quality policy",
            )

        digest = snapshot.dataset_id.removeprefix("sha256:")[:12]
        package_path = packages_root / f"{session_date.isoformat()}-{digest}"
        if package_path.exists():
            raise SinaMarketBreadthImportError(
                "SINA_BREADTH_OUTPUT_EXISTS",
                f"package already exists: {package_path}",
            )
        temporary.rename(package_path)
        current_temporary = root / f".current-{uuid.uuid4().hex}"
        os.symlink(Path("packages") / package_path.name, current_temporary)
        os.replace(current_temporary, root / "current")
        return SinaMarketBreadthImportReceipt(package_path=package_path, snapshot=snapshot)
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
        if current_temporary is not None and current_temporary.is_symlink():
            current_temporary.unlink()


def _iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be an ISO 8601 date") from error


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate an auditable EOD market-breadth package from Sina web quotes.",
    )
    parser.add_argument("--session-date", required=True, type=_iso_date)
    parser.add_argument("--universe-csv", required=True, type=Path)
    parser.add_argument("--universe-id", required=True)
    parser.add_argument("--universe-source", required=True)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument(
        "--batch-size",
        required=True,
        type=int,
        help="Explicit batch size previously validated by a bounded live contract probe (1-100).",
    )
    parser.add_argument("--max-capture-seconds", type=int, default=60)
    parser.add_argument(
        "--license-note",
        default=(
            "Local research only; authorization and redistribution rights for the "
            "undocumented Sina endpoint are not established."
        ),
    )
    parser.add_argument("--acknowledge-undocumented-sina", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        members = _load_universe_csv(args.universe_csv, session_date=args.session_date)
        receipt = generate_sina_market_breadth_package(
            universe_members=members,
            universe_id=args.universe_id,
            universe_source=args.universe_source,
            license_note=args.license_note,
            inclusion_rules=["listed Shanghai and Shenzhen A-share stocks"],
            exclusion_rules=["BSE, B shares, funds, bonds and indices"],
            session_date=args.session_date,
            output_root=args.output_root,
            acknowledge_undocumented_source=args.acknowledge_undocumented_sina,
            batch_size=args.batch_size,
            max_capture_seconds=args.max_capture_seconds,
        )
    except SinaMarketBreadthImportError as error:
        print(
            json.dumps(
                {"status": "REJECTED", "code": error.code, "message": error.message},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    except OSError as error:
        print(
            json.dumps(
                {
                    "status": "REJECTED",
                    "code": "SINA_BREADTH_IO_ERROR",
                    "message": str(error),
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 3

    snapshot = receipt.snapshot
    print(
        json.dumps(
            {
                "status": snapshot.status,
                "session_date": snapshot.session_date.isoformat(),
                "universe_total": snapshot.universe_total,
                "covered": snapshot.covered,
                "unavailable": snapshot.unavailable,
                "resolution_ratio": str(snapshot.resolution_ratio),
                "source": snapshot.source,
                "dataset_id": snapshot.dataset_id,
                "package": str(receipt.package_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
