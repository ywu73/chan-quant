from __future__ import annotations

from collections import Counter
from decimal import Decimal

from chan_quant.domain.market_breadth import (
    BreadthObservation,
    MarketBreadthBin,
    MarketBreadthBuildInput,
    MarketBreadthIssue,
    MarketBreadthSnapshot,
)

RESOLUTION_THRESHOLD = Decimal("0.995")

_BIN_SPECS = (
    ("lt_m7", "<-7%", "DECLINE"),
    ("m7_m5", "-7%~-5%", "DECLINE"),
    ("m5_m3", "-5%~-3%", "DECLINE"),
    ("m3_m2", "-3%~-2%", "DECLINE"),
    ("m2_m1", "-2%~-1%", "DECLINE"),
    ("m1_0", "-1%~0", "DECLINE"),
    ("p0_p1", "0~1%", "ADVANCE"),
    ("p1_p2", "1%~2%", "ADVANCE"),
    ("p2_p3", "2%~3%", "ADVANCE"),
    ("p3_p5", "3%~5%", "ADVANCE"),
    ("p5_p7", "5%~7%", "ADVANCE"),
    ("gt_p7", ">7%", "ADVANCE"),
)


class MarketBreadthBuildError(ValueError):
    """Raised when breadth input violates the versioned calculation contract."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


def _bin_id(change_ratio: Decimal) -> str:
    if change_ratio < Decimal("-0.07"):
        return "lt_m7"
    if change_ratio < Decimal("-0.05"):
        return "m7_m5"
    if change_ratio < Decimal("-0.03"):
        return "m5_m3"
    if change_ratio < Decimal("-0.02"):
        return "m3_m2"
    if change_ratio < Decimal("-0.01"):
        return "m2_m1"
    if change_ratio < 0:
        return "m1_0"
    if change_ratio <= Decimal("0.01"):
        return "p0_p1"
    if change_ratio <= Decimal("0.02"):
        return "p1_p2"
    if change_ratio <= Decimal("0.03"):
        return "p2_p3"
    if change_ratio <= Decimal("0.05"):
        return "p3_p5"
    if change_ratio <= Decimal("0.07"):
        return "p5_p7"
    return "gt_p7"


def _index_unique(values: list[object], *, key: str, code: str) -> dict[str, object]:
    indexed: dict[str, object] = {}
    for value in values:
        identity = getattr(value, key)
        if identity in indexed:
            raise MarketBreadthBuildError(code, f"duplicate symbol: {identity}")
        indexed[identity] = value
    return indexed


def _unavailable_reason(observation: BreadthObservation) -> str | None:
    if observation.unavailable_reason is not None:
        return observation.unavailable_reason
    if observation.previous_close is None or observation.previous_close == 0:
        return "NO_REFERENCE_PRICE"
    if observation.last_price is None or observation.last_price == 0:
        return "INVALID_PRICE"
    return None


def build_market_breadth(input_data: MarketBreadthBuildInput) -> MarketBreadthSnapshot:
    if not input_data.universe_members:
        raise MarketBreadthBuildError("UNIVERSE_EMPTY", "market breadth universe must not be empty")

    members = _index_unique(
        list(input_data.universe_members),
        key="symbol",
        code="UNIVERSE_DUPLICATE_SYMBOL",
    )
    observations = _index_unique(
        list(input_data.observations),
        key="symbol",
        code="QUOTE_DUPLICATE_SYMBOL",
    )
    extra_symbols = sorted(set(observations) - set(members))
    if extra_symbols:
        raise MarketBreadthBuildError(
            "QUOTE_SYMBOL_OUTSIDE_UNIVERSE",
            f"quote symbol is not in universe: {extra_symbols[0]}",
        )

    bin_counts: Counter[str] = Counter()
    unavailable_reasons: Counter[str] = Counter()
    issues: list[MarketBreadthIssue] = []
    advancers = 0
    decliners = 0
    unchanged = 0
    explicitly_unavailable = 0
    provider_mismatches = 0

    for symbol in members:
        observation = observations.get(symbol)
        if observation is None:
            unavailable_reasons["MISSING_QUOTE"] += 1
            continue
        assert isinstance(observation, BreadthObservation)
        if observation.session_date != input_data.session_date:
            raise MarketBreadthBuildError(
                "SESSION_DATE_MISMATCH",
                f"quote {symbol} has session date {observation.session_date}",
            )
        reason = _unavailable_reason(observation)
        if reason is not None:
            unavailable_reasons[reason] += 1
            explicitly_unavailable += 1
            continue

        assert observation.previous_close is not None
        assert observation.last_price is not None
        if observation.previous_close < 0 or observation.last_price < 0:
            raise MarketBreadthBuildError(
                "NEGATIVE_PRICE",
                f"quote {symbol} contains a negative price",
            )
        delta = observation.last_price - observation.previous_close
        if delta == 0:
            unchanged += 1
            continue

        change_ratio = delta / observation.previous_close
        bin_counts[_bin_id(change_ratio)] += 1
        if delta > 0:
            advancers += 1
        else:
            decliners += 1

        if observation.provider_change_percent is not None:
            provider_ratio = observation.provider_change_percent / Decimal(100)
            if abs(provider_ratio - change_ratio) > Decimal("0.000001"):
                provider_mismatches += 1

    if provider_mismatches:
        issues.append(
            MarketBreadthIssue(
                code="PROVIDER_CHANGE_PERCENT_MISMATCH",
                severity="WARNING",
                message=f"{provider_mismatches} 条提供方涨跌幅与后端复算不一致。",
            )
        )

    universe_total = len(members)
    covered = advancers + decliners + unchanged
    unavailable = universe_total - covered
    coverage_ratio = Decimal(covered) / Decimal(universe_total)
    resolution_ratio = Decimal(covered + explicitly_unavailable) / Decimal(universe_total)

    if covered == 0 or resolution_ratio < RESOLUTION_THRESHOLD:
        status = "FAILED"
        issues.append(
            MarketBreadthIssue(
                code="INSUFFICIENT_RESOLUTION",
                severity="DANGER",
                message=(
                    "行情可解释比例低于 market-breadth-quality-v0.1 的 99.5% 门槛，"
                    "不得展示涨跌分布。"
                ),
            )
        )
    elif resolution_ratio < 1:
        status = "PARTIAL"
        issues.append(
            MarketBreadthIssue(
                code="UNKNOWN_MISSING_QUOTES",
                severity="WARNING",
                message="存在无法由来源状态解释的缺失行情。",
            )
        )
    else:
        status = "COMPLETE"

    bins = [
        MarketBreadthBin(id=bin_id, label=label, side=side, count=bin_counts[bin_id])
        for bin_id, label, side in _BIN_SPECS
    ]

    if sum(item.count for item in bins) != advancers + decliners:
        raise MarketBreadthBuildError("BIN_INVARIANT_FAILED", "non-zero bin count mismatch")
    if covered + unavailable != universe_total:
        raise MarketBreadthBuildError("COVERAGE_INVARIANT_FAILED", "coverage count mismatch")

    return MarketBreadthSnapshot(
        status=status,
        market=input_data.market,
        mode=input_data.mode,
        session_date=input_data.session_date,
        universe_id=input_data.universe_id,
        universe_as_of=input_data.universe_as_of,
        snapshot_at=input_data.snapshot_at,
        received_at=input_data.received_at,
        source=input_data.source,
        dataset_id=input_data.dataset_id,
        quality_policy_version=input_data.quality_policy_version,
        calculation_policy_version=input_data.calculation_policy_version,
        universe_total=universe_total,
        covered=covered,
        unavailable=unavailable,
        explicitly_unavailable=explicitly_unavailable,
        coverage_ratio=coverage_ratio,
        resolution_ratio=resolution_ratio,
        advancers=advancers,
        decliners=decliners,
        unchanged=unchanged,
        bins=bins,
        unavailable_reasons=dict(sorted(unavailable_reasons.items())),
        issues=issues,
    )
