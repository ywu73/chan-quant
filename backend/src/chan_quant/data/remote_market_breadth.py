from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from chan_quant.data.exchange_universe_source import (
    ExchangeUniverseCapture,
    ExchangeUniverseSourceError,
    fetch_exchange_a_share_universe,
)
from chan_quant.data.sina_market_breadth_source import (
    SinaMarketBreadthCapture,
    SinaMarketBreadthSourceError,
    fetch_sina_market_breadth,
)
from chan_quant.domain.market_breadth import (
    MarketBreadthBuildInput,
    MarketBreadthIssue,
    MarketBreadthSnapshot,
)
from chan_quant.services.market_breadth import MarketBreadthBuildError, build_market_breadth

REMOTE_BREADTH_MAX_WORKERS = 3


class RemoteMarketBreadthError(ValueError):
    """Raised when a remote observation cannot satisfy the breadth contract."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class _CacheEntry:
    snapshot: MarketBreadthSnapshot
    stored_at: float


def _default_universe_source() -> ExchangeUniverseCapture:
    return fetch_exchange_a_share_universe(max_workers=REMOTE_BREADTH_MAX_WORKERS)


def _default_quote_source(symbols: list[str]) -> SinaMarketBreadthCapture:
    return fetch_sina_market_breadth(
        symbols,
        batch_size=100,
        max_workers=REMOTE_BREADTH_MAX_WORKERS,
    )


class RemoteMarketBreadthService:
    """Load one validated remote observation behind a cached, force-refreshable interface."""

    def __init__(
        self,
        *,
        universe_source: Callable[[], ExchangeUniverseCapture] = _default_universe_source,
        quote_source: Callable[[list[str]], SinaMarketBreadthCapture] = _default_quote_source,
        clock: Callable[[], datetime] | None = None,
        timer: Callable[[], float] = time.monotonic,
        cache_ttl_seconds: int = 300,
        max_capture_seconds: int = 60,
    ) -> None:
        if cache_ttl_seconds <= 0:
            raise ValueError("cache_ttl_seconds must be positive")
        if max_capture_seconds <= 0:
            raise ValueError("max_capture_seconds must be positive")
        self._universe_source = universe_source
        self._quote_source = quote_source
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._timer = timer
        self._cache_ttl_seconds = cache_ttl_seconds
        self._max_capture_seconds = max_capture_seconds
        self._cache: _CacheEntry | None = None
        self._lock = threading.Lock()

    def get(self, *, force_refresh: bool = False) -> MarketBreadthSnapshot:
        with self._lock:
            current_time = self._timer()
            if (
                not force_refresh
                and self._cache is not None
                and current_time - self._cache.stored_at < self._cache_ttl_seconds
            ):
                return self._cache.snapshot
            snapshot = self._load()
            self._cache = _CacheEntry(snapshot=snapshot, stored_at=self._timer())
            return snapshot

    def _load(self) -> MarketBreadthSnapshot:
        try:
            universe = self._universe_source()
            capture = self._quote_source([member.symbol for member in universe.members])
        except (ExchangeUniverseSourceError, SinaMarketBreadthSourceError) as error:
            raise RemoteMarketBreadthError(error.code, error.message) from error

        capture_seconds = (capture.completed_at - capture.started_at).total_seconds()
        if capture_seconds > self._max_capture_seconds:
            raise RemoteMarketBreadthError(
                "REMOTE_BREADTH_CAPTURE_WINDOW_EXCEEDED",
                f"remote capture window {capture_seconds:.3f}s exceeds {self._max_capture_seconds}s",
            )

        members = [
            member
            for member in universe.members
            if member.list_date <= capture.session_date
            and (member.delist_date is None or member.delist_date > capture.session_date)
        ]
        member_symbols = {member.symbol for member in members}
        observations = [
            observation
            for observation in capture.observations
            if observation.symbol in member_symbols
        ]
        try:
            snapshot = build_market_breadth(
                MarketBreadthBuildInput(
                    market="CN_A_SH_SZ_V1",
                    mode="OBSERVED",
                    session_date=capture.session_date,
                    universe_id=universe.universe_id,
                    universe_as_of=universe.universe_as_of,
                    snapshot_at=capture.completed_at,
                    received_at=self._clock(),
                    source="上交所/深交所官方列表 + 新浪未文档化行情",
                    dataset_id=(
                        "remote-observation:"
                        f"{capture.session_date.isoformat()}:"
                        f"{capture.completed_at.astimezone(timezone.utc).isoformat()}"
                    ),
                    quality_policy_version="market-breadth-quality-v0.1",
                    calculation_policy_version="market-breadth-calculation-v0.1",
                    universe_members=members,
                    observations=observations,
                )
            )
        except MarketBreadthBuildError as error:
            raise RemoteMarketBreadthError(error.code, error.message) from error

        provenance_issues = [
            MarketBreadthIssue(
                code="REMOTE_OBSERVATION_NOT_AUDITABLE",
                severity="WARNING",
                message=(
                    "当前结果来自运行时远端观测，没有保存逐批原始证据；"
                    "不能作为可复现的审计快照。"
                ),
            ),
            MarketBreadthIssue(
                code="SINA_UNDOCUMENTED_SOURCE",
                severity="WARNING",
                message=(
                    "行情来自未文档化新浪网页端点；没有字段承诺、服务等级或授权保证。"
                ),
            ),
        ]
        return snapshot.model_copy(update={"issues": [*snapshot.issues, *provenance_issues]})


remote_market_breadth_service = RemoteMarketBreadthService()
