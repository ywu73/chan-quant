from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from chan_quant.data.csv_source import CsvDataError, load_csv_bars
from chan_quant.domain.data_quality import (
    DataQualityIssue,
    DataQualityReport,
    MarketDataManifest,
)
from chan_quant.domain.market import MarketBar

MANIFEST_NAME = "manifest.json"
BARS_NAME = "bars.csv"


class MarketSnapshotError(ValueError):
    """Raised when a local market snapshot fails closed validation."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class LoadedMarketSnapshot:
    bars: list[MarketBar]
    manifest: MarketDataManifest
    quality: DataQualityReport


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _dataset_id(manifest: MarketDataManifest) -> str:
    canonical = json.dumps(
        manifest.model_dump(mode="json"),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def _load_manifest(path: Path) -> MarketDataManifest:
    if not path.is_file():
        raise MarketSnapshotError("MANIFEST_MISSING", f"manifest does not exist: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as error:
        raise MarketSnapshotError("MANIFEST_ENCODING", "manifest.json must be UTF-8") from error
    except json.JSONDecodeError as error:
        raise MarketSnapshotError(
            "MANIFEST_JSON_INVALID",
            f"manifest.json is invalid JSON at line {error.lineno} column {error.colno}",
        ) from error
    except OSError as error:
        raise MarketSnapshotError(
            "MANIFEST_READ_FAILED",
            f"cannot read manifest.json: {error}",
        ) from error
    try:
        return MarketDataManifest.model_validate(payload)
    except ValidationError as error:
        first = error.errors()[0]
        location = ".".join(str(part) for part in first["loc"]) or "manifest"
        raise MarketSnapshotError(
            "MANIFEST_CONTRACT_INVALID",
            f"{location}: {first['msg']}",
        ) from error


def load_market_snapshot(
    package_path: str | Path,
    *,
    expected_symbol: str,
) -> LoadedMarketSnapshot:
    root = Path(package_path).expanduser()
    if not root.is_dir():
        raise MarketSnapshotError("PACKAGE_MISSING", f"snapshot directory does not exist: {root}")

    manifest = _load_manifest(root / MANIFEST_NAME)
    canonical_expected = expected_symbol.strip().upper()
    if manifest.symbol != canonical_expected:
        raise MarketSnapshotError(
            "SYMBOL_MISMATCH",
            f"manifest symbol {manifest.symbol} does not match request {canonical_expected}",
        )

    bars_path = root / BARS_NAME
    if not bars_path.is_file():
        raise MarketSnapshotError("BARS_MISSING", f"bars file does not exist: {bars_path}")
    try:
        actual_sha256 = _sha256_file(bars_path)
    except OSError as error:
        raise MarketSnapshotError(
            "BARS_READ_FAILED",
            f"cannot read bars.csv: {error}",
        ) from error
    if not hmac.compare_digest(actual_sha256, manifest.bars_sha256):
        raise MarketSnapshotError(
            "HASH_MISMATCH",
            f"bars.csv SHA-256 {actual_sha256} does not match manifest {manifest.bars_sha256}",
        )

    try:
        bars = load_csv_bars(bars_path)
    except (CsvDataError, OSError) as error:
        raise MarketSnapshotError("BARS_CONTRACT_INVALID", str(error)) from error

    if len(bars) < 92:
        raise MarketSnapshotError(
            "BARS_CONTRACT_INVALID",
            f"expected at least 92 bars, got {len(bars)}",
        )

    if len(bars) != manifest.bar_count:
        raise MarketSnapshotError(
            "BAR_COUNT_MISMATCH",
            f"manifest declares {manifest.bar_count} bars but bars.csv contains {len(bars)}",
        )
    actual_from = bars[0].date
    actual_to = bars[-1].date
    if actual_from != manifest.data_from or actual_to != manifest.data_to:
        raise MarketSnapshotError(
            "DATE_RANGE_MISMATCH",
            (
                f"manifest range {manifest.data_from}..{manifest.data_to} does not match "
                f"bars.csv {actual_from}..{actual_to}"
            ),
        )

    issues: list[DataQualityIssue] = []
    if manifest.adjustment_basis == "provider-declared":
        issues.append(
            DataQualityIssue(
                code="ADJUSTMENT_PROVIDER_DECLARED",
                severity="WARNING",
                message=(
                    "复权口径来自数据提供方声明，当前数据包只验证文件与结构完整性，"
                    "尚未独立交叉验证复权经济含义。"
                ),
            )
        )
    else:
        issues.append(
            DataQualityIssue(
                code="ADJUSTMENT_EXTERNAL_AUDIT_REFERENCE",
                severity="INFO",
                message=(
                    "manifest 提供了外部复权审计引用；本应用记录该引用，"
                    "但不会自行验证外部材料的真实性或结论。"
                ),
            )
        )

    has_warning = any(issue.severity in {"WARNING", "DANGER"} for issue in issues)

    report = DataQualityReport(
        status="WARNING" if has_warning else "READY",
        integrity="MATCH",
        dataset_id=_dataset_id(manifest),
        schema_version=manifest.schema_version,
        provider=manifest.provider,
        adjustment=manifest.adjustment,
        adjustment_basis=manifest.adjustment_basis,
        timeframe=manifest.timeframe,
        timezone=manifest.timezone,
        fetched_at=manifest.fetched_at,
        data_from=manifest.data_from,
        data_to=manifest.data_to,
        bar_count=manifest.bar_count,
        bars_sha256=manifest.bars_sha256,
        license_note=manifest.license_note,
        audit_reference=manifest.audit_reference,
        issues=issues,
    )
    return LoadedMarketSnapshot(bars=bars, manifest=manifest, quality=report)
