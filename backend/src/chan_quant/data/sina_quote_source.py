from __future__ import annotations

import math
import re
from datetime import datetime, time, timedelta, timezone
from typing import cast

import httpx

from chan_quant.data.sina_source import SinaDataError, SinaUpstreamError, to_sina_symbol
from chan_quant.domain.quote import (
    QuoteBatch,
    QuoteFailure,
    QuoteSnapshot,
    QuoteStatus,
)

SINA_QUOTE_URL = "https://hq.sinajs.cn/"
SHANGHAI_TZ = timezone(timedelta(hours=8))
_QUOTE_PATTERN = re.compile(r'^var hq_str_(?P<symbol>[a-z]{2}\d{6})="(?P<fields>.*)";$')


class SinaQuoteUnavailableError(RuntimeError):
    """Raised when Sina returns no usable current snapshot for a valid request."""


def _status(quote_at: datetime, received_at: datetime) -> tuple[QuoteStatus, bool]:
    age = received_at - quote_at
    if quote_at.date() < received_at.date() or quote_at.time() >= time(15, 0):
        return "CLOSED", False
    if timedelta(0) <= age <= timedelta(seconds=30):
        return "LIVE", False
    return "DELAYED", True


def _number(raw: str, field: str) -> float:
    try:
        value = float(raw)
    except ValueError as error:
        raise SinaUpstreamError(f"Sina quote {field} is not numeric") from error
    if not math.isfinite(value):
        raise SinaUpstreamError(f"Sina quote {field} must be finite")
    return value


def _parse_quote_fields(
    raw_fields: str,
    *,
    symbol: str,
    received_at: datetime,
) -> QuoteSnapshot:
    if not raw_fields:
        raise SinaQuoteUnavailableError(f"Sina returned no current quote for {symbol}")
    fields = raw_fields.split(",")
    if len(fields) < 32:
        raise SinaUpstreamError("Sina quote response has fewer than 32 fields")

    name = fields[0].strip()
    if not name:
        raise SinaUpstreamError("Sina quote name is empty")
    last_price = _number(fields[3], "last_price")
    previous_close = _number(fields[2], "previous_close")
    open_price = _number(fields[1], "open")
    high = _number(fields[4], "high")
    low = _number(fields[5], "low")
    volume_number = _number(fields[8], "volume")
    if all(
        value == 0
        for value in (open_price, previous_close, last_price, high, low, volume_number)
    ):
        raise SinaQuoteUnavailableError(f"Sina returned a zero-valued quote for {symbol}")
    if all(value == 0 for value in (open_price, high, low, volume_number)):
        raise SinaQuoteUnavailableError(f"Sina returned a zero-range quote for {symbol}")
    if last_price <= 0:
        raise SinaUpstreamError("Sina quote last_price must be positive")
    if previous_close <= 0:
        raise SinaUpstreamError("Sina quote previous_close must be positive")
    if any(value < 0 for value in (open_price, high, low)):
        raise SinaUpstreamError("Sina quote OHLC prices must be non-negative")
    observed_prices = [last_price, *(value for value in (open_price,) if value > 0)]
    if high < max(observed_prices) or low <= 0 or low > min(observed_prices):
        raise SinaUpstreamError("Sina quote OHLC range is invalid")
    if volume_number < 0 or not volume_number.is_integer():
        raise SinaUpstreamError("Sina quote volume must be a non-negative integer")
    try:
        quote_at = datetime.fromisoformat(f"{fields[30]}T{fields[31]}").replace(
            tzinfo=SHANGHAI_TZ
        )
    except ValueError as error:
        raise SinaUpstreamError("Sina quote date or time is invalid") from error
    if quote_at - received_at > timedelta(seconds=5):
        raise SinaUpstreamError("Sina quote quote_at is later than received_at")
    status, is_stale = _status(quote_at, received_at)
    return QuoteSnapshot(
        symbol=symbol,
        name=name,
        last_price=last_price,
        previous_close=previous_close,
        change=round(last_price - previous_close, 6),
        change_percent=round((last_price / previous_close) - 1, 6),
        open=open_price,
        high=high,
        low=low,
        volume=int(volume_number),
        quote_at=quote_at,
        received_at=received_at,
        status=status,
        is_stale=is_stale,
    )


def _parse_quote_batch(
    content: bytes,
    *,
    requested_symbols: tuple[str, ...],
    received_at: datetime,
) -> QuoteBatch:
    try:
        text = content.decode("gb18030")
    except UnicodeDecodeError as error:
        raise SinaUpstreamError("Sina quote response is not valid GB18030") from error

    expected_by_sina = {
        to_sina_symbol(symbol): symbol for symbol in requested_symbols
    }
    outcomes: dict[str, QuoteSnapshot | QuoteFailure] = {}
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        match = _QUOTE_PATTERN.fullmatch(line.strip())
        if match is None:
            raise SinaUpstreamError(
                f"Sina quote response line {line_number} has an invalid assignment"
            )
        sina_symbol = match.group("symbol")
        symbol = expected_by_sina.get(sina_symbol)
        if symbol is None:
            if len(requested_symbols) == 1:
                raise SinaUpstreamError(
                    "Sina quote response symbol does not match the request"
                )
            raise SinaUpstreamError(
                f"Sina quote response contains unrequested symbol {sina_symbol}"
            )
        if symbol in outcomes:
            raise SinaUpstreamError(
                f"Sina quote response contains duplicate symbol {symbol}"
            )

        try:
            outcomes[symbol] = _parse_quote_fields(
                match.group("fields"),
                symbol=symbol,
                received_at=received_at,
            )
        except SinaQuoteUnavailableError as error:
            outcomes[symbol] = QuoteFailure(
                symbol=symbol,
                code="QUOTE_UNAVAILABLE",
                message=str(error),
            )
        except SinaUpstreamError as error:
            outcomes[symbol] = QuoteFailure(
                symbol=symbol,
                code="QUOTE_INVALID",
                message=str(error),
            )

    for symbol in requested_symbols:
        if symbol not in outcomes:
            outcomes[symbol] = QuoteFailure(
                symbol=symbol,
                code="QUOTE_OMITTED",
                message=f"Sina quote response omitted {symbol}",
            )

    quotes = [
        cast(QuoteSnapshot, outcomes[symbol])
        for symbol in requested_symbols
        if isinstance(outcomes[symbol], QuoteSnapshot)
    ]
    failures = [
        cast(QuoteFailure, outcomes[symbol])
        for symbol in requested_symbols
        if isinstance(outcomes[symbol], QuoteFailure)
    ]
    status = "COMPLETE" if not failures else "FAILED" if not quotes else "PARTIAL"
    return QuoteBatch(
        status=status,
        requested=list(requested_symbols),
        succeeded=len(quotes),
        failed=len(failures),
        quotes=quotes,
        failures=failures,
    )


def fetch_sina_quotes(
    symbols: list[str] | tuple[str, ...],
    *,
    client: httpx.Client | None = None,
    received_at: datetime | None = None,
) -> QuoteBatch:
    canonical_symbols = tuple(symbol.strip().upper() for symbol in symbols)
    if not 1 <= len(canonical_symbols) <= 8:
        raise SinaDataError("Sina batch quote requires 1 to 8 symbols")
    if len(set(canonical_symbols)) != len(canonical_symbols):
        raise SinaDataError("Sina batch quote symbols must be distinct")
    sina_symbols = tuple(to_sina_symbol(symbol) for symbol in canonical_symbols)

    owns_client = client is None
    http_client = client or httpx.Client(follow_redirects=False)
    try:
        # Sina treats an encoded comma (%2C) as part of one symbol. Keep literal
        # commas in the URL, matching the already audited breadth reader.
        batch_url = f"{SINA_QUOTE_URL}?list={','.join(sina_symbols)}"
        try:
            response = http_client.get(
                batch_url,
                headers={
                    "Accept": "text/plain, */*",
                    "Referer": "https://finance.sina.com.cn/",
                    "User-Agent": "ChanQuant/0.2 local-research",
                },
                timeout=httpx.Timeout(connect=3.0, read=5.0, write=3.0, pool=3.0),
            )
        except httpx.HTTPError as error:
            raise SinaUpstreamError(f"Sina quote request failed: {error}") from error
        if response.status_code != 200:
            raise SinaUpstreamError(
                f"Sina quote request returned HTTP {response.status_code}"
            )
        observed_at = received_at or datetime.now(SHANGHAI_TZ)
        return _parse_quote_batch(
            response.content,
            requested_symbols=canonical_symbols,
            received_at=observed_at,
        )
    finally:
        if owns_client:
            http_client.close()


def fetch_sina_quote(
    symbol: str,
    *,
    client: httpx.Client | None = None,
    received_at: datetime | None = None,
) -> QuoteSnapshot:
    batch = fetch_sina_quotes(
        [symbol],
        client=client,
        received_at=received_at,
    )
    if batch.quotes:
        return batch.quotes[0]

    failure = batch.failures[0]
    if failure.code == "QUOTE_UNAVAILABLE":
        raise SinaQuoteUnavailableError(failure.message)
    raise SinaUpstreamError(failure.message)
