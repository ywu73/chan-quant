from datetime import date, datetime
from decimal import Decimal

import pytest

from chan_quant.domain.market_breadth import (
    BreadthObservation,
    BreadthUniverseMember,
    MarketBreadthBuildInput,
)
from chan_quant.services.market_breadth import MarketBreadthBuildError, build_market_breadth


def _member(index: int) -> BreadthUniverseMember:
    exchange = "SH" if index % 2 else "SZ"
    return BreadthUniverseMember(
        symbol=f"{index:06d}.{exchange}",
        exchange=exchange,
        security_name=f"测试股票 {index}",
        security_type="A_STOCK",
        board="MAIN",
        list_date=date(2020, 1, 1),
    )


def _input(
    members: list[BreadthUniverseMember],
    observations: list[BreadthObservation],
) -> MarketBreadthBuildInput:
    return MarketBreadthBuildInput(
        market="CN_A_SH_SZ_V1",
        mode="EOD",
        session_date=date(2026, 7, 31),
        universe_id="official-sh-sz-2026-07-31",
        universe_as_of=date(2026, 7, 31),
        snapshot_at=datetime.fromisoformat("2026-08-01T16:05:00+08:00"),
        received_at=datetime.fromisoformat("2026-08-02T15:00:00+08:00"),
        source="authorized-test-export",
        dataset_id="sha256:test",
        quality_policy_version="market-breadth-quality-v0.1",
        calculation_policy_version="market-breadth-calculation-v0.1",
        universe_members=members,
        observations=observations,
    )


def test_market_breadth_assigns_every_non_zero_boundary_once_and_keeps_zero_separate() -> None:
    changes = [
        Decimal("-0.08"),
        Decimal("-0.07"),
        Decimal("-0.05"),
        Decimal("-0.03"),
        Decimal("-0.02"),
        Decimal("-0.01"),
        Decimal(0),
        Decimal("0.01"),
        Decimal("0.02"),
        Decimal("0.03"),
        Decimal("0.05"),
        Decimal("0.07"),
        Decimal("0.08"),
    ]
    members = [_member(index) for index in range(1, len(changes) + 1)]
    observations = [
        BreadthObservation(
            symbol=member.symbol,
            session_date=date(2026, 7, 31),
            previous_close=Decimal(100),
            last_price=Decimal(100) * (Decimal(1) + change),
        )
        for member, change in zip(members, changes, strict=True)
    ]

    snapshot = build_market_breadth(_input(members, observations))

    assert snapshot.status == "COMPLETE"
    assert snapshot.universe_total == 13
    assert snapshot.covered == 13
    assert snapshot.unavailable == 0
    assert snapshot.advancers == 6
    assert snapshot.decliners == 6
    assert snapshot.unchanged == 1
    assert [item.id for item in snapshot.bins] == [
        "lt_m7",
        "m7_m5",
        "m5_m3",
        "m3_m2",
        "m2_m1",
        "m1_0",
        "p0_p1",
        "p1_p2",
        "p2_p3",
        "p3_p5",
        "p5_p7",
        "gt_p7",
    ]
    assert [item.count for item in snapshot.bins] == [1] * 12
    assert sum(item.count for item in snapshot.bins) == (
        snapshot.advancers + snapshot.decliners
    )
    assert snapshot.advancers + snapshot.decliners + snapshot.unchanged == snapshot.covered
    assert snapshot.covered + snapshot.unavailable == snapshot.universe_total
    assert snapshot.coverage_ratio == Decimal(1)
    assert snapshot.resolution_ratio == Decimal(1)


def test_market_breadth_distinguishes_explicit_unavailable_from_unknown_missing_rows() -> None:
    members = [_member(index) for index in range(1, 201)]
    observations = [
        BreadthObservation(
            symbol=member.symbol,
            session_date=date(2026, 7, 31),
            previous_close=Decimal(10),
            last_price=Decimal(11),
        )
        for member in members[:198]
    ]
    observations.append(
        BreadthObservation(
            symbol=members[198].symbol,
            session_date=date(2026, 7, 31),
            unavailable_reason="SUSPENDED",
        )
    )

    snapshot = build_market_breadth(_input(members, observations))

    assert snapshot.status == "PARTIAL"
    assert snapshot.covered == 198
    assert snapshot.unavailable == 2
    assert snapshot.explicitly_unavailable == 1
    assert snapshot.unavailable_reasons == {"MISSING_QUOTE": 1, "SUSPENDED": 1}
    assert snapshot.coverage_ratio == Decimal("0.99")
    assert snapshot.resolution_ratio == Decimal("0.995")


def test_market_breadth_fails_distribution_when_resolution_is_below_policy_threshold() -> None:
    members = [_member(index) for index in range(1, 101)]
    observations = [
        BreadthObservation(
            symbol=member.symbol,
            session_date=date(2026, 7, 31),
            previous_close=Decimal(10),
            last_price=Decimal(9),
        )
        for member in members[:99]
    ]

    snapshot = build_market_breadth(_input(members, observations))

    assert snapshot.status == "FAILED"
    assert snapshot.resolution_ratio == Decimal("0.99")
    assert [issue.code for issue in snapshot.issues] == ["INSUFFICIENT_RESOLUTION"]


@pytest.mark.parametrize(
    ("observations", "code"),
    [
        (
            [
                BreadthObservation(
                    symbol="000001.SH",
                    session_date=date(2026, 7, 31),
                    previous_close=Decimal(10),
                    last_price=Decimal(11),
                ),
                BreadthObservation(
                    symbol="000001.SH",
                    session_date=date(2026, 7, 31),
                    previous_close=Decimal(10),
                    last_price=Decimal(11),
                ),
            ],
            "QUOTE_DUPLICATE_SYMBOL",
        ),
        (
            [
                BreadthObservation(
                    symbol="000001.SH",
                    session_date=date(2026, 7, 30),
                    previous_close=Decimal(10),
                    last_price=Decimal(11),
                )
            ],
            "SESSION_DATE_MISMATCH",
        ),
        (
            [
                BreadthObservation(
                    symbol="000001.SH",
                    session_date=date(2026, 7, 31),
                    previous_close=Decimal(10),
                    last_price=Decimal(-1),
                )
            ],
            "NEGATIVE_PRICE",
        ),
    ],
)
def test_market_breadth_rejects_ambiguous_or_invalid_observations(
    observations: list[BreadthObservation],
    code: str,
) -> None:
    member = _member(1)

    with pytest.raises(MarketBreadthBuildError, match=code):
        build_market_breadth(_input([member], observations))
