import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from chan_quant.data.market_breadth_package import (
    MarketBreadthPackageError,
    load_market_breadth_package,
)
from chan_quant.domain.market_breadth import BreadthUniverseMember
from chan_quant.importers.sina_market_breadth import (
    SinaMarketBreadthImportError,
    generate_sina_market_breadth_package,
)

SHANGHAI_TZ = timezone(timedelta(hours=8))


def _quote_line(
    symbol: str,
    *,
    name: str,
    previous_close: str,
    last_price: str,
) -> str:
    fields = [
        name,
        last_price,
        previous_close,
        last_price,
        last_price,
        last_price,
        last_price,
        last_price,
        "100",
        "1000",
        *(["0"] * 20),
        "2026-07-31",
        "15:01:02",
    ]
    return f'var hq_str_{symbol}="{",".join(fields)}";'


def _universe() -> list[BreadthUniverseMember]:
    return [
        BreadthUniverseMember(
            symbol="000001.SZ",
            exchange="SZ",
            security_name="平安银行",
            security_type="A_STOCK",
            board="MAIN",
            list_date=date(1991, 4, 3),
        ),
        BreadthUniverseMember(
            symbol="600000.SH",
            exchange="SH",
            security_name="浦发银行",
            security_type="A_STOCK",
            board="MAIN",
            list_date=date(1999, 11, 10),
        ),
    ]


def test_importer_atomically_publishes_a_v2_package_with_raw_sina_evidence(
    tmp_path: Path,
) -> None:
    requested_at = datetime(2026, 7, 31, 15, 5, tzinfo=SHANGHAI_TZ)
    completed_at = datetime(2026, 7, 31, 15, 5, 1, tzinfo=SHANGHAI_TZ)
    clock_values = iter([requested_at, completed_at])

    def handler(_: httpx.Request) -> httpx.Response:
        content = "\n".join(
            [
                _quote_line(
                    "sz000001",
                    name="平安银行",
                    previous_close="11.610",
                    last_price="11.630",
                ),
                _quote_line(
                    "sh600000",
                    name="浦发银行",
                    previous_close="9.710",
                    last_price="9.510",
                ),
            ]
        ).encode("gb18030")
        return httpx.Response(200, content=content)

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        receipt = generate_sina_market_breadth_package(
            universe_members=_universe(),
            universe_id="official-sh-sz-test-2026-07-31",
            universe_source="official-exchange-test-fixture",
            license_note="Synthetic test rows only",
            inclusion_rules=["listed Shanghai and Shenzhen A-share stocks"],
            exclusion_rules=["BSE, B shares, funds, bonds and indices"],
            session_date=date(2026, 7, 31),
            output_root=tmp_path / "breadth",
            acknowledge_undocumented_source=True,
            batch_size=100,
            client=client,
            clock=lambda: next(clock_values),
        )

    assert receipt.snapshot.status == "COMPLETE"
    assert receipt.package_path.is_dir()
    assert (tmp_path / "breadth" / "current").resolve() == receipt.package_path.resolve()
    assert (receipt.package_path / "evidence" / "sina-quotes-batch-0001.txt").is_file()

    manifest = json.loads((receipt.package_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "market-breadth-package-v0.2"
    assert manifest["session_date_evidence"] == "provider-row-date"
    assert manifest["request_count"] == 1
    assert manifest["evidence_files"][0]["path"] == "evidence/sina-quotes-batch-0001.txt"

    reloaded = load_market_breadth_package(receipt.package_path)
    assert reloaded.dataset_id == receipt.snapshot.dataset_id
    assert [issue.code for issue in reloaded.issues] == ["SINA_UNDOCUMENTED_SOURCE"]

    evidence_path = receipt.package_path / "evidence" / "sina-quotes-batch-0001.txt"
    evidence_path.write_bytes(b"tampered")
    with pytest.raises(MarketBreadthPackageError, match="EVIDENCE_SIZE_MISMATCH"):
        load_market_breadth_package(receipt.package_path)


def test_importer_rejects_a_stale_provider_date_without_publishing_current(
    tmp_path: Path,
) -> None:
    received_at = datetime(2026, 7, 31, 15, 5, tzinfo=SHANGHAI_TZ)
    clock_values = iter([received_at, received_at])

    def handler(_: httpx.Request) -> httpx.Response:
        stale = _quote_line(
            "sz000001",
            name="平安银行",
            previous_close="11.610",
            last_price="11.630",
        ).replace("2026-07-31", "2026-07-30")
        return httpx.Response(200, content=stale.encode("gb18030"))

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(SinaMarketBreadthImportError) as captured,
    ):
        generate_sina_market_breadth_package(
            universe_members=_universe()[:1],
            universe_id="official-sh-sz-test-2026-07-31",
            universe_source="official-exchange-test-fixture",
            license_note="Synthetic test rows only",
            inclusion_rules=["listed Shanghai and Shenzhen A-share stocks"],
            exclusion_rules=["BSE, B shares, funds, bonds and indices"],
            session_date=date(2026, 7, 31),
            output_root=tmp_path / "breadth",
            acknowledge_undocumented_source=True,
            batch_size=100,
            client=client,
            clock=lambda: next(clock_values),
        )

    assert captured.value.code == "SINA_BREADTH_SESSION_DATE_MISMATCH"
    assert not (tmp_path / "breadth" / "current").exists()


def test_importer_rejects_a_capture_window_that_is_too_wide(tmp_path: Path) -> None:
    requested_at = datetime(2026, 7, 31, 15, 5, tzinfo=SHANGHAI_TZ)
    completed_at = datetime(2026, 7, 31, 15, 6, 1, tzinfo=SHANGHAI_TZ)
    clock_values = iter([requested_at, completed_at])

    def handler(_: httpx.Request) -> httpx.Response:
        content = _quote_line(
            "sz000001",
            name="平安银行",
            previous_close="11.610",
            last_price="11.630",
        ).encode("gb18030")
        return httpx.Response(200, content=content)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(SinaMarketBreadthImportError) as captured,
    ):
        generate_sina_market_breadth_package(
            universe_members=_universe()[:1],
            universe_id="official-sh-sz-test-2026-07-31",
            universe_source="official-exchange-test-fixture",
            license_note="Synthetic test rows only",
            inclusion_rules=["listed Shanghai and Shenzhen A-share stocks"],
            exclusion_rules=["BSE, B shares, funds, bonds and indices"],
            session_date=date(2026, 7, 31),
            output_root=tmp_path / "breadth",
            acknowledge_undocumented_source=True,
            batch_size=100,
            max_capture_seconds=60,
            client=client,
            clock=lambda: next(clock_values),
        )

    assert captured.value.code == "SINA_BREADTH_CAPTURE_WINDOW_EXCEEDED"
    assert not (tmp_path / "breadth" / "current").exists()


def test_importer_rejects_an_invalid_universe_identity_at_its_interface(
    tmp_path: Path,
) -> None:
    invalid = _universe()[0].model_copy(update={"symbol": "000001.BJ"})

    with pytest.raises(SinaMarketBreadthImportError) as captured:
        generate_sina_market_breadth_package(
            universe_members=[invalid],
            universe_id="invalid-test-universe",
            universe_source="synthetic-invalid-fixture",
            license_note="Synthetic test rows only",
            inclusion_rules=["invalid test fixture"],
            exclusion_rules=["none"],
            session_date=date(2026, 7, 31),
            output_root=tmp_path / "breadth",
            acknowledge_undocumented_source=True,
            batch_size=1,
        )

    assert captured.value.code == "SINA_BREADTH_IDENTITY_INVALID"
