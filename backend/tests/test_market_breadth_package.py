import csv
import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chan_quant.api.app import app
from chan_quant.data.market_breadth_package import (
    MarketBreadthPackageError,
    load_market_breadth_package,
)
from chan_quant.data.remote_market_breadth import RemoteMarketBreadthError


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_package(root: Path) -> dict[str, object]:
    root.mkdir()
    universe_rows = [
        {
            "symbol": "000001.SZ",
            "exchange": "SZ",
            "security_name": "平安银行测试",
            "security_type": "A_STOCK",
            "board": "MAIN",
            "list_date": "1991-04-03",
            "delist_date": "",
        },
        {
            "symbol": "300001.SZ",
            "exchange": "SZ",
            "security_name": "创业板测试",
            "security_type": "A_STOCK",
            "board": "CHINEXT",
            "list_date": "2009-10-30",
            "delist_date": "",
        },
        {
            "symbol": "600000.SH",
            "exchange": "SH",
            "security_name": "沪市主板测试",
            "security_type": "A_STOCK",
            "board": "MAIN",
            "list_date": "1999-11-10",
            "delist_date": "",
        },
        {
            "symbol": "688001.SH",
            "exchange": "SH",
            "security_name": "科创板测试",
            "security_type": "A_STOCK",
            "board": "STAR",
            "list_date": "2019-07-22",
            "delist_date": "",
        },
    ]
    quote_rows = [
        {
            "symbol": "000001.SZ",
            "session_date": "2026-07-31",
            "previous_close": "10",
            "last_price": "11",
            "unavailable_reason": "",
            "provider_change_percent": "10",
        },
        {
            "symbol": "300001.SZ",
            "session_date": "2026-07-31",
            "previous_close": "10",
            "last_price": "9",
            "unavailable_reason": "",
            "provider_change_percent": "-10",
        },
        {
            "symbol": "600000.SH",
            "session_date": "2026-07-31",
            "previous_close": "10",
            "last_price": "10",
            "unavailable_reason": "",
            "provider_change_percent": "0",
        },
        {
            "symbol": "688001.SH",
            "session_date": "2026-07-31",
            "previous_close": "",
            "last_price": "",
            "unavailable_reason": "SUSPENDED",
            "provider_change_percent": "",
        },
    ]
    universe_path = root / "universe.csv"
    quotes_path = root / "quotes.csv"
    _write_csv(universe_path, list(universe_rows[0]), universe_rows)
    _write_csv(quotes_path, list(quote_rows[0]), quote_rows)
    manifest: dict[str, object] = {
        "schema_version": "market-breadth-package-v0.1",
        "market": "CN_A_SH_SZ_V1",
        "mode": "EOD",
        "timezone": "Asia/Shanghai",
        "session_date": "2026-07-31",
        "universe_id": "official-sh-sz-test-2026-07-31",
        "universe_as_of": "2026-07-31",
        "fetched_at": "2026-08-01T16:05:00+08:00",
        "source": "authorized-test-export",
        "universe_source": "official-exchange-test-fixture",
        "quote_source": "authorized-provider-test-fixture",
        "license_note": "Synthetic rows for contract tests only",
        "inclusion_rules": ["listed Shanghai and Shenzhen A-share stocks"],
        "exclusion_rules": ["BSE, B shares, funds, bonds and indices"],
        "universe_row_count": len(universe_rows),
        "quotes_row_count": len(quote_rows),
        "universe_bytes": universe_path.stat().st_size,
        "quotes_bytes": quotes_path.stat().st_size,
        "universe_sha256": hashlib.sha256(universe_path.read_bytes()).hexdigest(),
        "quotes_sha256": hashlib.sha256(quotes_path.read_bytes()).hexdigest(),
        "quality_policy_version": "market-breadth-quality-v0.1",
        "calculation_policy_version": "market-breadth-calculation-v0.1",
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def test_auditable_market_breadth_package_recomputes_distribution_and_identity(
    tmp_path: Path,
) -> None:
    package = tmp_path / "breadth"
    _write_package(package)

    first = load_market_breadth_package(package)
    second = load_market_breadth_package(package)

    assert first.status == "COMPLETE"
    assert first.market == "CN_A_SH_SZ_V1"
    assert first.mode == "EOD"
    assert first.universe_total == 4
    assert first.covered == 3
    assert first.unavailable == 1
    assert first.explicitly_unavailable == 1
    assert first.advancers == 1
    assert first.decliners == 1
    assert first.unchanged == 1
    assert first.unavailable_reasons == {"SUSPENDED": 1}
    assert first.dataset_id == second.dataset_id
    assert first.dataset_id == (
        "sha256:b137babb37fc65556e1f6e1a30262760fce8c274a43f2f35c6bae1d1917fd187"
    )


def test_market_breadth_endpoint_exposes_remote_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "breadth"
    _write_package(package)
    snapshot = load_market_breadth_package(package).model_copy(update={"mode": "OBSERVED"})

    class FakeRemoteService:
        def get(self, *, force_refresh: bool = False):
            assert force_refresh is True
            return snapshot

    monkeypatch.setattr(
        "chan_quant.api.app.remote_market_breadth_service",
        FakeRemoteService(),
    )

    response = TestClient(app).get(
        "/api/v1/market-breadth",
        params={"market": "CN_A_SH_SZ_V1", "refresh": "true"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETE"
    assert payload["session_date"] == "2026-07-31"
    assert payload["universe_as_of"] == "2026-07-31"
    assert payload["source"] == "authorized-test-export"
    assert payload["coverage_ratio"] == 0.75
    assert payload["resolution_ratio"] == 1.0
    assert len(payload["bins"]) == 12


def test_market_breadth_package_rejects_tampered_quote_rows(tmp_path: Path) -> None:
    package = tmp_path / "breadth"
    _write_package(package)
    quotes_path = package / "quotes.csv"
    original = quotes_path.read_bytes()
    quotes_path.write_bytes(original.replace(b",10,11,,10\r\n", b",10,12,,10\r\n", 1))

    with pytest.raises(MarketBreadthPackageError, match="QUOTES_HASH_MISMATCH"):
        load_market_breadth_package(package)


def test_market_breadth_package_rejects_evidence_symlink_outside_package(
    tmp_path: Path,
) -> None:
    package = tmp_path / "breadth"
    manifest = _write_package(package)
    outside_evidence = tmp_path / "outside-sina-response.txt"
    outside_evidence.write_bytes(b'var hq_str_sz000001="fixture";\n')
    evidence_dir = package / "evidence"
    evidence_dir.mkdir()
    evidence_path = evidence_dir / "sina-quotes-batch-0001.txt"
    evidence_path.symlink_to(outside_evidence)
    manifest.update(
        {
            "schema_version": "market-breadth-package-v0.2",
            "session_date_evidence": "provider-row-date",
            "snapshot_started_at": "2026-07-31T15:05:00+08:00",
            "snapshot_completed_at": "2026-07-31T15:05:01+08:00",
            "quote_contract": "sina-hq-undocumented-observed-v0.1",
            "request_batch_size": 4,
            "request_count": 1,
            "evidence_files": [
                {
                    "path": "evidence/sina-quotes-batch-0001.txt",
                    "bytes": outside_evidence.stat().st_size,
                    "sha256": hashlib.sha256(outside_evidence.read_bytes()).hexdigest(),
                }
            ],
        }
    )
    (package / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(MarketBreadthPackageError) as captured:
        load_market_breadth_package(package)

    assert captured.value.code == "EVIDENCE_PATH_INVALID"


def test_market_breadth_endpoint_maps_remote_failure_without_stale_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingRemoteService:
        def get(self, *, force_refresh: bool = False):
            raise RemoteMarketBreadthError(
                "SINA_BREADTH_HTTP_ERROR",
                "Sina breadth request returned HTTP 503",
            )

    monkeypatch.setattr(
        "chan_quant.api.app.remote_market_breadth_service",
        FailingRemoteService(),
    )

    response = TestClient(app).get("/api/v1/market-breadth")

    assert response.status_code == 502
    assert response.json()["detail"] == {
        "status": "REJECTED",
        "code": "SINA_BREADTH_HTTP_ERROR",
        "message": "Sina breadth request returned HTTP 503",
    }


def test_market_breadth_endpoint_rejects_unsupported_market() -> None:
    response = TestClient(app).get(
        "/api/v1/market-breadth",
        params={"market": "CN_A_ALL"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "status": "REJECTED",
        "code": "MARKET_UNSUPPORTED",
        "message": "market must be CN_A_SH_SZ_V1",
    }
