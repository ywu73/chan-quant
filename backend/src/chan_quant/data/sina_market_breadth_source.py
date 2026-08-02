from __future__ import annotations

import re
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from datetime import time as quote_time_type
from decimal import Decimal, InvalidOperation

import httpx

from chan_quant.data.sina_source import to_sina_symbol
from chan_quant.domain.market_breadth import BreadthObservation

SINA_QUOTE_URL = "https://hq.sinajs.cn/"
SHANGHAI_TZ = timezone(timedelta(hours=8))
_ASSIGNMENT_PATTERN = re.compile(r'^var hq_str_(?P<symbol>[a-z]{2}\d{6})="(?P<fields>.*)";$')


class SinaMarketBreadthSourceError(ValueError):
    """Raised when Sina batch data cannot satisfy the breadth import contract."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class SinaRawBatch:
    index: int
    symbols: tuple[str, ...]
    requested_at: datetime
    received_at: datetime
    content: bytes


@dataclass(frozen=True)
class SinaMarketBreadthCapture:
    observations: tuple[BreadthObservation, ...]
    raw_batches: tuple[SinaRawBatch, ...]
    started_at: datetime
    completed_at: datetime
    request_count: int
    batch_size: int
    session_date: date


def _decimal(raw: str, *, symbol: str, field: str) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation as error:
        raise SinaMarketBreadthSourceError(
            "SINA_BREADTH_PRICE_INVALID",
            f"{symbol} {field} is not decimal",
        ) from error
    if not value.is_finite():
        raise SinaMarketBreadthSourceError(
            "SINA_BREADTH_PRICE_INVALID",
            f"{symbol} {field} must be finite",
        )
    return value


def _parse_batch(
    content: bytes,
    *,
    requested_symbols: Sequence[str],
    expected_session_date: date | None,
) -> tuple[dict[str, BreadthObservation], date]:
    try:
        text = content.decode("gb18030")
    except UnicodeDecodeError as error:
        raise SinaMarketBreadthSourceError(
            "SINA_BREADTH_ENCODING_INVALID",
            "Sina breadth response is not valid GB18030",
        ) from error

    expected_by_sina = {to_sina_symbol(symbol): symbol for symbol in requested_symbols}
    parsed: dict[str, BreadthObservation] = {}
    observed_session_date = expected_session_date
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        match = _ASSIGNMENT_PATTERN.fullmatch(line.strip())
        if match is None:
            raise SinaMarketBreadthSourceError(
                "SINA_BREADTH_ASSIGNMENT_INVALID",
                f"line {line_number} is not a Sina quote assignment",
            )
        sina_symbol = match.group("symbol")
        symbol = expected_by_sina.get(sina_symbol)
        if symbol is None:
            raise SinaMarketBreadthSourceError(
                "SINA_BREADTH_UNEXPECTED_SYMBOL",
                f"Sina returned unrequested symbol {sina_symbol}",
            )
        if symbol in parsed:
            raise SinaMarketBreadthSourceError(
                "SINA_BREADTH_DUPLICATE_SYMBOL",
                f"Sina returned duplicate symbol {symbol}",
            )

        raw_fields = match.group("fields")
        if not raw_fields:
            raise SinaMarketBreadthSourceError(
                "SINA_BREADTH_MISSING_QUOTE",
                f"Sina returned an empty quote without provider date for {symbol}",
            )
        fields = raw_fields.split(",")
        if len(fields) < 32:
            raise SinaMarketBreadthSourceError(
                "SINA_BREADTH_ASSIGNMENT_INVALID",
                f"{symbol} has fewer than 32 fields",
            )
        try:
            quote_date = date.fromisoformat(fields[30])
        except ValueError as error:
            raise SinaMarketBreadthSourceError(
                "SINA_BREADTH_SESSION_DATE_INVALID",
                f"{symbol} quote date is invalid",
            ) from error
        if observed_session_date is None:
            observed_session_date = quote_date
        if quote_date != observed_session_date:
            raise SinaMarketBreadthSourceError(
                "SINA_BREADTH_SESSION_DATE_MISMATCH",
                f"{symbol} quote date {quote_date} does not match {observed_session_date}",
            )
        try:
            quote_time_type.fromisoformat(fields[31])
        except ValueError as error:
            raise SinaMarketBreadthSourceError(
                "SINA_BREADTH_QUOTE_TIME_INVALID",
                f"{symbol} quote time is invalid",
            ) from error
        previous_close = _decimal(fields[2], symbol=symbol, field="previous_close")
        last_price = _decimal(fields[3], symbol=symbol, field="last_price")
        if previous_close <= 0 or last_price <= 0:
            parsed[symbol] = BreadthObservation(
                symbol=symbol,
                session_date=quote_date,
                unavailable_reason="INVALID_PRICE",
            )
            continue
        parsed[symbol] = BreadthObservation(
            symbol=symbol,
            session_date=quote_date,
            previous_close=previous_close,
            last_price=last_price,
        )

    missing = [symbol for symbol in requested_symbols if symbol not in parsed]
    if missing:
        raise SinaMarketBreadthSourceError(
            "SINA_BREADTH_MISSING_SYMBOL",
            f"Sina response omitted {missing[0]}",
        )
    if observed_session_date is None:
        raise SinaMarketBreadthSourceError(
            "SINA_BREADTH_SESSION_DATE_MISSING",
            "Sina breadth response did not expose a provider session date",
        )
    return parsed, observed_session_date


def fetch_sina_market_breadth(
    symbols: Sequence[str],
    *,
    session_date: date | None = None,
    batch_size: int = 100,
    client: httpx.Client | None = None,
    clock: Callable[[], datetime] | None = None,
    max_retries: int = 2,
    sleeper: Callable[[float], None] = time.sleep,
) -> SinaMarketBreadthCapture:
    if not symbols:
        raise SinaMarketBreadthSourceError(
            "SINA_BREADTH_UNIVERSE_EMPTY",
            "Sina breadth import requires at least one symbol",
        )
    if not 1 <= batch_size <= 100:
        raise SinaMarketBreadthSourceError(
            "SINA_BREADTH_BATCH_SIZE_INVALID",
            "Sina breadth batch size must be between 1 and 100",
        )
    if not 0 <= max_retries <= 2:
        raise SinaMarketBreadthSourceError(
            "SINA_BREADTH_RETRY_LIMIT_INVALID",
            "Sina breadth retry limit must be between 0 and 2",
        )
    canonical_symbols = tuple(symbol.strip().upper() for symbol in symbols)
    if len(set(canonical_symbols)) != len(canonical_symbols):
        raise SinaMarketBreadthSourceError(
            "SINA_BREADTH_DUPLICATE_SYMBOL",
            "Sina breadth request contains duplicate symbols",
        )

    now = clock or (lambda: datetime.now(SHANGHAI_TZ))
    started_at = now()
    owns_client = client is None
    http_client = client or httpx.Client(follow_redirects=False)
    observations: dict[str, BreadthObservation] = {}
    raw_batches: list[SinaRawBatch] = []
    observed_session_date = session_date
    try:
        for offset in range(0, len(canonical_symbols), batch_size):
            batch = canonical_symbols[offset : offset + batch_size]
            requested_at = started_at if not raw_batches else raw_batches[-1].received_at
            response: httpx.Response | None = None
            last_error: httpx.HTTPError | None = None
            batch_url = (
                f"{SINA_QUOTE_URL}?list={','.join(to_sina_symbol(symbol) for symbol in batch)}"
            )
            for attempt in range(max_retries + 1):
                try:
                    candidate = http_client.get(
                        batch_url,
                        headers={
                            "Accept": "text/plain, */*",
                            "Referer": "https://finance.sina.com.cn/",
                            "User-Agent": "ChanQuant/0.2 local-research",
                        },
                        timeout=httpx.Timeout(
                            connect=3.0,
                            read=10.0,
                            write=3.0,
                            pool=3.0,
                        ),
                    )
                except httpx.HTTPError as error:
                    last_error = error
                    if attempt < max_retries:
                        sleeper(0.25 * (2**attempt))
                        continue
                    break
                if candidate.status_code >= 500 and attempt < max_retries:
                    sleeper(0.25 * (2**attempt))
                    continue
                response = candidate
                break
            if response is None:
                assert last_error is not None
                raise SinaMarketBreadthSourceError(
                    "SINA_BREADTH_HTTP_ERROR",
                    f"Sina breadth request failed: {last_error}",
                ) from last_error
            if response.status_code == 429:
                raise SinaMarketBreadthSourceError(
                    "SINA_BREADTH_RATE_LIMITED",
                    "Sina breadth request returned HTTP 429",
                )
            if response.status_code != 200:
                raise SinaMarketBreadthSourceError(
                    "SINA_BREADTH_HTTP_ERROR",
                    f"Sina breadth request returned HTTP {response.status_code}",
                )
            received_at = now()
            parsed, observed_session_date = _parse_batch(
                response.content,
                requested_symbols=batch,
                expected_session_date=observed_session_date,
            )
            observations.update(parsed)
            raw_batches.append(
                SinaRawBatch(
                    index=len(raw_batches) + 1,
                    symbols=tuple(batch),
                    requested_at=requested_at,
                    received_at=received_at,
                    content=response.content,
                )
            )
    finally:
        if owns_client:
            http_client.close()

    completed_at = raw_batches[-1].received_at
    return SinaMarketBreadthCapture(
        observations=tuple(observations[symbol] for symbol in canonical_symbols),
        raw_batches=tuple(raw_batches),
        started_at=started_at,
        completed_at=completed_at,
        request_count=len(raw_batches),
        batch_size=batch_size,
        session_date=observed_session_date,
    )
