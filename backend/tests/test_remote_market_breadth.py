from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from chan_quant.data.exchange_universe_source import (
    ExchangeUniverseCapture,
    ExchangeUniverseSourceError,
)
from chan_quant.data.remote_market_breadth import (
    RemoteMarketBreadthError,
    RemoteMarketBreadthService,
)
from chan_quant.data.sina_market_breadth_source import SinaMarketBreadthCapture
from chan_quant.domain.market_breadth import BreadthObservation, BreadthUniverseMember

SHANGHAI_TZ = timezone(timedelta(hours=8))


def _universe() -> ExchangeUniverseCapture:
    observed_at = datetime(2026, 8, 2, 20, 0, tzinfo=SHANGHAI_TZ)
    return ExchangeUniverseCapture(
        members=(
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
        ),
        universe_id="sse-szse-live-observed-2026-08-02",
        universe_as_of=date(2026, 8, 2),
        observed_at=observed_at,
    )


def _quotes() -> SinaMarketBreadthCapture:
    started_at = datetime(2026, 8, 2, 20, 0, 1, tzinfo=SHANGHAI_TZ)
    completed_at = datetime(2026, 8, 2, 20, 0, 2, tzinfo=SHANGHAI_TZ)
    return SinaMarketBreadthCapture(
        observations=(
            BreadthObservation(
                symbol="000001.SZ",
                session_date=date(2026, 7, 31),
                previous_close=Decimal("11.61"),
                last_price=Decimal("11.63"),
            ),
            BreadthObservation(
                symbol="600000.SH",
                session_date=date(2026, 7, 31),
                previous_close=Decimal("9.71"),
                last_price=Decimal("9.51"),
            ),
        ),
        raw_batches=(),
        started_at=started_at,
        completed_at=completed_at,
        request_count=1,
        batch_size=100,
        session_date=date(2026, 7, 31),
    )


def test_remote_service_builds_observed_snapshot_and_caches_success() -> None:
    calls = {"universe": 0, "quotes": 0}
    now_seconds = [10.0]

    def fetch_universe() -> ExchangeUniverseCapture:
        calls["universe"] += 1
        return _universe()

    def fetch_quotes(symbols: list[str]) -> SinaMarketBreadthCapture:
        calls["quotes"] += 1
        assert symbols == ["000001.SZ", "600000.SH"]
        return _quotes()

    service = RemoteMarketBreadthService(
        universe_source=fetch_universe,
        quote_source=fetch_quotes,
        clock=lambda: datetime(2026, 8, 2, 12, 0, 3, tzinfo=timezone.utc),
        timer=lambda: now_seconds[0],
        cache_ttl_seconds=300,
    )

    first = service.get()
    now_seconds[0] = 20.0
    second = service.get()

    assert first == second
    assert calls == {"universe": 1, "quotes": 1}
    assert first.mode == "OBSERVED"
    assert first.session_date == date(2026, 7, 31)
    assert first.universe_as_of == date(2026, 8, 2)
    assert first.source == "上交所/深交所官方列表 + 新浪未文档化行情"
    assert first.dataset_id.startswith("remote-observation:")
    assert first.status == "COMPLETE"
    assert first.advancers == 1
    assert first.decliners == 1
    assert [issue.code for issue in first.issues] == [
        "REMOTE_OBSERVATION_NOT_AUDITABLE",
        "SINA_UNDOCUMENTED_SOURCE",
    ]


def test_remote_service_force_refresh_bypasses_success_cache() -> None:
    calls = 0

    def fetch_universe() -> ExchangeUniverseCapture:
        nonlocal calls
        calls += 1
        return _universe()

    service = RemoteMarketBreadthService(
        universe_source=fetch_universe,
        quote_source=lambda _: _quotes(),
        timer=lambda: 10.0,
    )

    service.get()
    service.get(force_refresh=True)

    assert calls == 2


def test_remote_service_force_refresh_surfaces_failure_instead_of_returning_stale_cache() -> None:
    should_fail = False

    def fetch_universe() -> ExchangeUniverseCapture:
        if should_fail:
            raise ExchangeUniverseSourceError(
                "EXCHANGE_UNIVERSE_HTTP_ERROR",
                "SSE returned HTTP 503",
            )
        return _universe()

    service = RemoteMarketBreadthService(
        universe_source=fetch_universe,
        quote_source=lambda _: _quotes(),
        timer=lambda: 10.0,
    )
    service.get()
    should_fail = True

    with pytest.raises(RemoteMarketBreadthError) as captured:
        service.get(force_refresh=True)

    assert captured.value.code == "EXCHANGE_UNIVERSE_HTTP_ERROR"
