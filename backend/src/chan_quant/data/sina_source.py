from __future__ import annotations

import json
import re
from datetime import date

import httpx

from chan_quant.domain.market import MarketBar, validate_bar_sequence

SINA_KLINE_URL = (
    "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/"
    "CN_MarketData.getKLineData"
)
_CANONICAL_SYMBOL = re.compile(r"^(?P<code>\d{6})\.(?P<exchange>SZ|SH)$")


class SinaDataError(ValueError):
    """Raised when a request or symbol violates the Sina adapter contract."""


class SinaUpstreamError(RuntimeError):
    """Raised when the undocumented Sina endpoint is unavailable or malformed."""


def to_sina_symbol(symbol: str) -> str:
    canonical = symbol.strip().upper()
    match = _CANONICAL_SYMBOL.fullmatch(canonical)
    if match is None:
        raise SinaDataError("Sina K-line source supports only NNNNNN.SZ or NNNNNN.SH")
    return f"{match.group('exchange').lower()}{match.group('code')}"


def _parse_payload(content: bytes, symbol: str) -> list[dict[str, object]]:
    try:
        payload = json.loads(content.decode("gb18030"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SinaUpstreamError("Sina K-line response is not valid GB18030 JSON") from error

    if payload is None:
        raise SinaDataError(f"Sina returned no K-line data for {symbol}")
    if isinstance(payload, dict) and payload.get("__ERROR"):
        message = payload.get("__ERRORMSG", "input error")
        raise SinaDataError(f"Sina rejected the K-line request: {message}")
    if not isinstance(payload, list):
        raise SinaUpstreamError("Sina K-line response must be a JSON array")
    return payload


def _normalize_rows(rows: list[dict[str, object]]) -> list[MarketBar]:
    bars: list[MarketBar] = []
    for row_number, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise SinaUpstreamError(f"Sina K-line row {row_number} must be an object")
        try:
            bars.append(
                MarketBar(
                    date=date.fromisoformat(str(row["day"])),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=int(float(row["volume"])),
                    amount=None,
                )
            )
        except (KeyError, TypeError, ValueError) as error:
            raise SinaUpstreamError(f"invalid Sina K-line row {row_number}: {error}") from error

    bars.sort(key=lambda item: item.date)
    try:
        validate_bar_sequence(bars)
    except ValueError as error:
        raise SinaUpstreamError(f"invalid Sina K-line sequence: {error}") from error
    return bars


def fetch_sina_kline_bars(
    symbol: str,
    *,
    datalen: int = 2_000,
    client: httpx.Client | None = None,
) -> list[MarketBar]:
    if not 1 <= datalen <= 10_000:
        raise SinaDataError("Sina datalen must be between 1 and 10000")

    sina_symbol = to_sina_symbol(symbol)
    owns_client = client is None
    http_client = client or httpx.Client(follow_redirects=False)
    try:
        try:
            response = http_client.get(
                SINA_KLINE_URL,
                params={
                    "symbol": sina_symbol,
                    "scale": "240",
                    "ma": "no",
                    "datalen": str(datalen),
                },
                headers={
                    "Accept": "application/json",
                    "User-Agent": "ChanQuant/0.2 local-research",
                },
                timeout=10.0,
            )
        except httpx.HTTPError as error:
            raise SinaUpstreamError(f"Sina K-line request failed: {error}") from error

        if response.status_code != 200:
            raise SinaUpstreamError(
                f"Sina K-line request returned HTTP {response.status_code}"
            )
        return _normalize_rows(_parse_payload(response.content, symbol.upper()))
    finally:
        if owns_client:
            http_client.close()
