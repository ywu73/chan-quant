import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chan_quant.api.app import app
from chan_quant.data.market_snapshot import MarketSnapshotError, load_market_snapshot
from chan_quant.domain.market import MarketBar
from chan_quant.services.demo_market import build_demo_bars


def _write_bars(path: Path, bars: list[MarketBar]) -> None:
    rows = ["trade_date,open,high,low,close,volume,amount"]
    for bar in bars:
        rows.append(
            ",".join(
                [
                    bar.date.isoformat(),
                    str(bar.open),
                    str(bar.high),
                    str(bar.low),
                    str(bar.close),
                    str(bar.volume),
                    "" if bar.amount is None else str(bar.amount),
                ]
            )
        )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _write_snapshot(
    root: Path,
    *,
    count: int = 140,
    manifest_overrides: dict[str, object] | None = None,
) -> tuple[list[MarketBar], dict[str, object]]:
    root.mkdir()
    bars = build_demo_bars(count=count)
    bars_path = root / "bars.csv"
    _write_bars(bars_path, bars)
    payload: dict[str, object] = {
        "schema_version": "market-snapshot-v0.1",
        "symbol": "000001.SZ",
        "instrument_name": "平安银行测试快照",
        "asset_type": "UNKNOWN",
        "price_precision": 2,
        "timeframe": "1d",
        "provider": "authorized-local-export",
        "adjustment": "qfq",
        "adjustment_basis": "provider-declared",
        "timezone": "Asia/Shanghai",
        "fetched_at": "2026-08-01T00:30:00+08:00",
        "data_from": bars[0].date.isoformat(),
        "data_to": bars[-1].date.isoformat(),
        "bar_count": len(bars),
        "bars_sha256": hashlib.sha256(bars_path.read_bytes()).hexdigest(),
        "license_note": "User-authorized local research export",
        "audit_reference": None,
    }
    payload.update(manifest_overrides or {})
    (root / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return bars, payload


def test_market_snapshot_loads_stable_identity_and_provider_warning(tmp_path: Path) -> None:
    package = tmp_path / "snapshot"
    bars, payload = _write_snapshot(package)

    first = load_market_snapshot(package, expected_symbol="000001.sz")
    (package / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    second = load_market_snapshot(package, expected_symbol="000001.SZ")

    assert first.bars == bars
    assert first.manifest.symbol == "000001.SZ"
    assert first.quality.dataset_id == second.quality.dataset_id
    assert first.quality.dataset_id.startswith("sha256:")
    assert first.quality.integrity == "MATCH"
    assert first.quality.status == "WARNING"
    assert first.quality.bars_sha256 == payload["bars_sha256"]
    assert [issue.code for issue in first.quality.issues] == ["ADJUSTMENT_PROVIDER_DECLARED"]


def test_market_snapshot_accepts_referenced_external_adjustment_audit(tmp_path: Path) -> None:
    package = tmp_path / "snapshot"
    _write_snapshot(
        package,
        manifest_overrides={
            "adjustment_basis": "externally-audited",
            "audit_reference": "local-audit-report-2026-08-01",
        },
    )

    loaded = load_market_snapshot(package, expected_symbol="000001.SZ")

    assert loaded.quality.status == "READY"
    assert [issue.code for issue in loaded.quality.issues] == [
        "ADJUSTMENT_EXTERNAL_AUDIT_REFERENCE"
    ]
    assert loaded.quality.issues[0].severity == "INFO"
    assert loaded.quality.audit_reference == "local-audit-report-2026-08-01"


def test_market_snapshot_rejects_tampered_bars_before_parsing(tmp_path: Path) -> None:
    package = tmp_path / "snapshot"
    _write_snapshot(package)
    with (package / "bars.csv").open("a", encoding="utf-8") as handle:
        handle.write("\n")

    with pytest.raises(MarketSnapshotError, match="HASH_MISMATCH"):
        load_market_snapshot(package, expected_symbol="000001.SZ")


def test_market_snapshot_rejects_insufficient_history_at_package_boundary(
    tmp_path: Path,
) -> None:
    package = tmp_path / "snapshot"
    _write_snapshot(package, count=91)

    with pytest.raises(MarketSnapshotError, match="expected at least 92 bars, got 91"):
        load_market_snapshot(package, expected_symbol="000001.SZ")


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"bar_count": 999}, "BAR_COUNT_MISMATCH"),
        ({"data_from": "2020-01-01"}, "DATE_RANGE_MISMATCH"),
        ({"timeframe": "5m"}, "MANIFEST_CONTRACT_INVALID"),
        (
            {"adjustment_basis": "externally-audited", "audit_reference": None},
            "MANIFEST_CONTRACT_INVALID",
        ),
    ],
)
def test_market_snapshot_rejects_manifest_contract_mismatches(
    tmp_path: Path,
    overrides: dict[str, object],
    message: str,
) -> None:
    package = tmp_path / "snapshot"
    _write_snapshot(package, manifest_overrides=overrides)

    with pytest.raises(MarketSnapshotError, match=message):
        load_market_snapshot(package, expected_symbol="000001.SZ")


def test_market_snapshot_rejects_requested_symbol_mismatch(tmp_path: Path) -> None:
    package = tmp_path / "snapshot"
    _write_snapshot(package)

    with pytest.raises(MarketSnapshotError, match="SYMBOL_MISMATCH"):
        load_market_snapshot(package, expected_symbol="600519.SH")


def test_snapshot_dashboard_exposes_quality_and_keeps_identity_across_as_of(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "snapshot"
    bars, _ = _write_snapshot(package)
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "snapshot")
    monkeypatch.setenv("CHAN_QUANT_DATA_PACKAGE_PATH", str(package))
    client = TestClient(app)

    full_response = client.get("/api/v1/instruments/000001.sz/dashboard")
    as_of_response = client.get(
        "/api/v1/instruments/000001.sz/dashboard",
        params={"as_of": bars[-10].date.isoformat()},
    )

    assert full_response.status_code == 200
    assert as_of_response.status_code == 200
    full = full_response.json()
    truncated = as_of_response.json()
    assert full["instrument"]["symbol"] == "000001.SZ"
    assert full["instrument"]["name"] == "平安银行测试快照"
    assert full["instrument"]["data_source"] == "auditable-market-snapshot"
    assert full["instrument"]["adjustment"] == "qfq"
    assert full["data_quality"]["status"] == "WARNING"
    assert full["data_quality"]["integrity"] == "MATCH"
    assert full["data_quality"]["bar_count"] == 140
    assert full["data_quality"]["dataset_id"] == truncated["data_quality"]["dataset_id"]
    assert full["instrument"]["as_of"] == bars[-1].date.isoformat()
    assert truncated["instrument"]["as_of"] == bars[-10].date.isoformat()
    assert full["recommendation"]["warnings"][0]["type"] == ("ADJUSTMENT_PROVIDER_DECLARED")


def test_snapshot_dashboard_requires_package_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "snapshot")
    monkeypatch.delenv("CHAN_QUANT_DATA_PACKAGE_PATH", raising=False)

    response = TestClient(app).get("/api/v1/instruments/000001.sz/dashboard")

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "CHAN_QUANT_DATA_PACKAGE_PATH is required in snapshot mode"
    )


def test_snapshot_dashboard_returns_structured_rejection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "snapshot"
    _write_snapshot(package)
    with (package / "bars.csv").open("a", encoding="utf-8") as handle:
        handle.write("\n")
    monkeypatch.setenv("CHAN_QUANT_DATA_SOURCE", "snapshot")
    monkeypatch.setenv("CHAN_QUANT_DATA_PACKAGE_PATH", str(package))

    response = TestClient(app).get("/api/v1/instruments/000001.sz/dashboard")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert set(detail) == {"status", "code", "message"}
    assert detail["status"] == "REJECTED"
    assert detail["code"] == "HASH_MISMATCH"
    assert "does not match manifest" in detail["message"]


def test_snapshot_path_selects_snapshot_mode_when_source_is_implicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "snapshot"
    _write_snapshot(package)
    monkeypatch.delenv("CHAN_QUANT_DATA_SOURCE", raising=False)
    monkeypatch.delenv("CHAN_QUANT_CSV_PATH", raising=False)
    monkeypatch.setenv("CHAN_QUANT_DATA_PACKAGE_PATH", str(package))

    health = TestClient(app).get("/health")
    dashboard = TestClient(app).get("/api/v1/instruments/000001.sz/dashboard")

    assert health.status_code == 200
    assert health.json()["data_mode"] == "snapshot"
    assert dashboard.status_code == 200
    assert dashboard.json()["instrument"]["data_source"] == "auditable-market-snapshot"
