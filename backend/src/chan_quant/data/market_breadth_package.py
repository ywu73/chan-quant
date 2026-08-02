from __future__ import annotations

import csv
import hashlib
import hmac
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from chan_quant.domain.market_breadth import (
    BreadthObservation,
    BreadthUniverseMember,
    MarketBreadthBuildInput,
    MarketBreadthSnapshot,
)
from chan_quant.services.market_breadth import MarketBreadthBuildError, build_market_breadth

MANIFEST_NAME = "manifest.json"
UNIVERSE_NAME = "universe.csv"
QUOTES_NAME = "quotes.csv"
_SYMBOL_PATTERN = re.compile(r"^\d{6}\.(SH|SZ)$")
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


class MarketBreadthPackageError(ValueError):
    """Raised when an external market-breadth package fails closed validation."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class MarketBreadthManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["market-breadth-package-v0.1"]
    market: Literal["CN_A_SH_SZ_V1"]
    mode: Literal["EOD"]
    timezone: Literal["Asia/Shanghai"]
    session_date: date
    universe_id: str = Field(min_length=1)
    universe_as_of: date
    fetched_at: datetime
    source: str = Field(min_length=1)
    universe_source: str = Field(min_length=1)
    quote_source: str = Field(min_length=1)
    license_note: str = Field(min_length=1)
    inclusion_rules: list[str] = Field(min_length=1)
    exclusion_rules: list[str] = Field(min_length=1)
    universe_row_count: int = Field(gt=0)
    quotes_row_count: int = Field(ge=0)
    universe_bytes: int = Field(gt=0)
    quotes_bytes: int = Field(gt=0)
    universe_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    quotes_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    quality_policy_version: Literal["market-breadth-quality-v0.1"]
    calculation_policy_version: Literal["market-breadth-calculation-v0.1"]

    @model_validator(mode="after")
    def validate_dates(self) -> MarketBreadthManifest:
        if self.universe_as_of != self.session_date:
            raise ValueError("universe_as_of must equal session_date")
        if self.fetched_at.tzinfo is None or self.fetched_at.utcoffset() is None:
            raise ValueError("fetched_at must include a UTC offset")
        return self


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dataset_id(manifest: MarketBreadthManifest) -> str:
    canonical = json.dumps(
        manifest.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def _load_manifest(path: Path) -> MarketBreadthManifest:
    if not path.is_file():
        raise MarketBreadthPackageError("MANIFEST_MISSING", f"manifest does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as error:
        raise MarketBreadthPackageError("MANIFEST_ENCODING", "manifest.json must be UTF-8") from error
    except json.JSONDecodeError as error:
        raise MarketBreadthPackageError(
            "MANIFEST_JSON_INVALID",
            f"manifest.json is invalid JSON at line {error.lineno} column {error.colno}",
        ) from error
    except OSError as error:
        raise MarketBreadthPackageError("MANIFEST_READ_FAILED", str(error)) from error
    try:
        return MarketBreadthManifest.model_validate(payload)
    except ValidationError as error:
        first = error.errors()[0]
        location = ".".join(str(part) for part in first["loc"]) or "manifest"
        raise MarketBreadthPackageError(
            "MANIFEST_CONTRACT_INVALID",
            f"{location}: {first['msg']}",
        ) from error


def _verify_file(
    path: Path,
    *,
    expected_size: int,
    expected_hash: str,
    missing_code: str,
    size_code: str,
    hash_code: str,
) -> None:
    if not path.is_file():
        raise MarketBreadthPackageError(missing_code, f"file does not exist: {path}")
    try:
        actual_size = path.stat().st_size
        actual_hash = _sha256_file(path)
    except OSError as error:
        raise MarketBreadthPackageError("PACKAGE_READ_FAILED", str(error)) from error
    if actual_size != expected_size:
        raise MarketBreadthPackageError(
            size_code,
            f"expected {expected_size} bytes but found {actual_size}",
        )
    if not hmac.compare_digest(actual_hash, expected_hash):
        raise MarketBreadthPackageError(
            hash_code,
            f"SHA-256 {actual_hash} does not match manifest {expected_hash}",
        )


def _read_rows(path: Path, expected_fields: list[str], *, code: str) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != expected_fields:
                raise MarketBreadthPackageError(
                    code,
                    f"expected CSV header {','.join(expected_fields)}",
                )
            rows = list(reader)
    except UnicodeDecodeError as error:
        raise MarketBreadthPackageError(code, f"{path.name} must be UTF-8") from error
    except csv.Error as error:
        raise MarketBreadthPackageError(code, str(error)) from error
    except OSError as error:
        raise MarketBreadthPackageError(code, f"cannot read {path.name}: {error}") from error
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise MarketBreadthPackageError(code, f"{path.name} contains a malformed row")
    return rows


def _parse_date(value: str, *, field: str, code: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except ValueError as error:
        raise MarketBreadthPackageError(code, f"{field} must be an ISO 8601 date") from error


def _optional_decimal(value: str, *, field: str) -> Decimal | None:
    normalized = value.strip()
    if not normalized:
        return None
    try:
        parsed = Decimal(normalized)
    except InvalidOperation as error:
        raise MarketBreadthPackageError(
            "QUOTES_CONTRACT_INVALID",
            f"{field} must be a finite decimal",
        ) from error
    if not parsed.is_finite():
        raise MarketBreadthPackageError(
            "QUOTES_CONTRACT_INVALID",
            f"{field} must be a finite decimal",
        )
    return parsed


def _load_universe(path: Path, manifest: MarketBreadthManifest) -> list[BreadthUniverseMember]:
    rows = _read_rows(path, _UNIVERSE_FIELDS, code="UNIVERSE_CONTRACT_INVALID")
    if len(rows) != manifest.universe_row_count:
        raise MarketBreadthPackageError(
            "UNIVERSE_ROW_COUNT_MISMATCH",
            f"manifest declares {manifest.universe_row_count} rows but CSV contains {len(rows)}",
        )
    members: list[BreadthUniverseMember] = []
    for row in rows:
        symbol = row["symbol"].strip().upper()
        exchange = row["exchange"].strip().upper()
        if not _SYMBOL_PATTERN.fullmatch(symbol) or symbol.rsplit(".", 1)[1] != exchange:
            raise MarketBreadthPackageError(
                "UNIVERSE_IDENTITY_INVALID",
                f"invalid or inconsistent symbol/exchange: {symbol}/{exchange}",
            )
        list_date = _parse_date(
            row["list_date"],
            field="list_date",
            code="UNIVERSE_CONTRACT_INVALID",
        )
        delist_date = (
            _parse_date(
                row["delist_date"],
                field="delist_date",
                code="UNIVERSE_CONTRACT_INVALID",
            )
            if row["delist_date"].strip()
            else None
        )
        if list_date > manifest.session_date or (
            delist_date is not None and delist_date <= manifest.session_date
        ):
            raise MarketBreadthPackageError(
                "UNIVERSE_MEMBER_OUTSIDE_SESSION",
                f"{symbol} was not listed for session {manifest.session_date}",
            )
        try:
            members.append(
                BreadthUniverseMember(
                    symbol=symbol,
                    exchange=exchange,
                    security_name=row["security_name"].strip(),
                    security_type=row["security_type"].strip().upper(),
                    board=row["board"].strip().upper(),
                    list_date=list_date,
                    delist_date=delist_date,
                )
            )
        except ValidationError as error:
            raise MarketBreadthPackageError(
                "UNIVERSE_CONTRACT_INVALID",
                f"{symbol}: {error.errors()[0]['msg']}",
            ) from error
    return members


def _load_quotes(path: Path, manifest: MarketBreadthManifest) -> list[BreadthObservation]:
    rows = _read_rows(path, _QUOTE_FIELDS, code="QUOTES_CONTRACT_INVALID")
    if len(rows) != manifest.quotes_row_count:
        raise MarketBreadthPackageError(
            "QUOTES_ROW_COUNT_MISMATCH",
            f"manifest declares {manifest.quotes_row_count} rows but CSV contains {len(rows)}",
        )
    observations: list[BreadthObservation] = []
    for row in rows:
        symbol = row["symbol"].strip().upper()
        if not _SYMBOL_PATTERN.fullmatch(symbol):
            raise MarketBreadthPackageError(
                "QUOTE_IDENTITY_INVALID",
                f"invalid quote symbol: {symbol}",
            )
        try:
            observations.append(
                BreadthObservation(
                    symbol=symbol,
                    session_date=_parse_date(
                        row["session_date"],
                        field="session_date",
                        code="QUOTES_CONTRACT_INVALID",
                    ),
                    previous_close=_optional_decimal(
                        row["previous_close"], field="previous_close"
                    ),
                    last_price=_optional_decimal(row["last_price"], field="last_price"),
                    unavailable_reason=row["unavailable_reason"].strip() or None,
                    provider_change_percent=_optional_decimal(
                        row["provider_change_percent"],
                        field="provider_change_percent",
                    ),
                )
            )
        except ValidationError as error:
            raise MarketBreadthPackageError(
                "QUOTES_CONTRACT_INVALID",
                f"{symbol}: {error.errors()[0]['msg']}",
            ) from error
    return observations


def load_market_breadth_package(package_path: str | Path) -> MarketBreadthSnapshot:
    root = Path(package_path).expanduser()
    if not root.is_dir():
        raise MarketBreadthPackageError(
            "PACKAGE_MISSING",
            f"market breadth package directory does not exist: {root}",
        )
    manifest = _load_manifest(root / MANIFEST_NAME)
    universe_path = root / UNIVERSE_NAME
    quotes_path = root / QUOTES_NAME
    _verify_file(
        universe_path,
        expected_size=manifest.universe_bytes,
        expected_hash=manifest.universe_sha256,
        missing_code="UNIVERSE_MISSING",
        size_code="UNIVERSE_SIZE_MISMATCH",
        hash_code="UNIVERSE_HASH_MISMATCH",
    )
    _verify_file(
        quotes_path,
        expected_size=manifest.quotes_bytes,
        expected_hash=manifest.quotes_sha256,
        missing_code="QUOTES_MISSING",
        size_code="QUOTES_SIZE_MISMATCH",
        hash_code="QUOTES_HASH_MISMATCH",
    )
    members = _load_universe(universe_path, manifest)
    observations = _load_quotes(quotes_path, manifest)
    try:
        return build_market_breadth(
            MarketBreadthBuildInput(
                market=manifest.market,
                mode=manifest.mode,
                session_date=manifest.session_date,
                universe_id=manifest.universe_id,
                universe_as_of=manifest.universe_as_of,
                snapshot_at=manifest.fetched_at,
                received_at=datetime.now(timezone.utc),
                source=manifest.source,
                dataset_id=_dataset_id(manifest),
                quality_policy_version=manifest.quality_policy_version,
                calculation_policy_version=manifest.calculation_policy_version,
                universe_members=members,
                observations=observations,
            )
        )
    except (MarketBreadthBuildError, ValidationError) as error:
        if isinstance(error, MarketBreadthBuildError):
            raise MarketBreadthPackageError(error.code, error.message) from error
        raise MarketBreadthPackageError(
            "PACKAGE_CONTRACT_INVALID",
            error.errors()[0]["msg"],
        ) from error
