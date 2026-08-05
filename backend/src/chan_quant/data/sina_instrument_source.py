from __future__ import annotations

import re

import httpx

from chan_quant.data.sina_source import SinaDataError, SinaUpstreamError
from chan_quant.domain.instrument import AssetType, InstrumentIdentity

SINA_SUGGEST_URL = "https://suggest3.sinajs.cn/suggest/"
SUGGEST_VARIABLE = "chan_quant_suggest"

_ASSIGNMENT_PATTERN = re.compile(rf'^var {SUGGEST_VARIABLE}="(?P<records>.*)";$')
_SINA_SYMBOL_PATTERN = re.compile(r"^(?P<exchange>sh|sz)(?P<code>\d{6})$")
_SUPPORTED_SECURITY_TYPES: dict[str, tuple[AssetType, int]] = {
    # Type 11 can include both equities and index aliases in observed responses,
    # so the undocumented provider category is not strong enough to classify it.
    "11": ("UNKNOWN", 2),
    # Type 203 consistently identified exchange-traded funds in the ETF samples
    # checked on 2026-07-31. This remains an observed, undocumented contract.
    "203": ("ETF", 3),
}


def _parse_suggestions(content: bytes, *, limit: int) -> list[InstrumentIdentity]:
    try:
        text = content.decode("gb18030")
    except UnicodeDecodeError as error:
        raise SinaUpstreamError("Sina suggest response is not valid GB18030") from error

    match = _ASSIGNMENT_PATTERN.fullmatch(text.strip())
    if match is None:
        raise SinaUpstreamError("Sina suggest response has an invalid assignment")

    raw_records = match.group("records")
    if not raw_records:
        return []

    items: list[InstrumentIdentity] = []
    seen_symbols: set[str] = set()
    for row_number, record in enumerate(raw_records.split(";"), start=1):
        fields = record.split(",")
        if len(fields) < 5:
            raise SinaUpstreamError(f"Sina suggest row {row_number} has fewer than 5 fields")

        security_type = fields[1].strip()
        code = fields[2].strip()
        provider_symbol = fields[3].strip().lower()
        name = fields[4].strip()
        symbol_match = _SINA_SYMBOL_PATTERN.fullmatch(provider_symbol)
        type_metadata = _SUPPORTED_SECURITY_TYPES.get(security_type)

        # Ignore unsupported categories and non-exchange symbols such as the
        # provider's `of` fund aliases instead of broadening product scope.
        if type_metadata is None or symbol_match is None:
            continue
        if code != symbol_match.group("code"):
            raise SinaUpstreamError(f"Sina suggest row {row_number} code does not match its symbol")
        if not name:
            raise SinaUpstreamError(f"Sina suggest row {row_number} name is empty")

        exchange = symbol_match.group("exchange").upper()
        asset_type, price_precision = type_metadata
        symbol = f"{code}.{exchange}"
        if symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)
        items.append(
            InstrumentIdentity(
                symbol=symbol,
                name=name,
                exchange=exchange,
                asset_type=asset_type,
                price_precision=price_precision,
                provider_symbols={"sina": provider_symbol},
            )
        )
        if len(items) >= limit:
            break
    return items


def search_sina_instruments(
    query: str,
    *,
    limit: int = 8,
    client: httpx.Client | None = None,
) -> list[InstrumentIdentity]:
    normalized_query = query.strip()
    if not normalized_query:
        raise SinaDataError("instrument search query must not be empty")
    if len(normalized_query) > 40:
        raise SinaDataError("instrument search query must not exceed 40 characters")
    if not 1 <= limit <= 20:
        raise SinaDataError("instrument search limit must be between 1 and 20")

    owns_client = client is None
    http_client = client or httpx.Client(follow_redirects=False)
    try:
        try:
            response = http_client.get(
                SINA_SUGGEST_URL,
                params={
                    "type": ",".join(_SUPPORTED_SECURITY_TYPES),
                    "key": normalized_query,
                    "name": SUGGEST_VARIABLE,
                },
                headers={
                    "Accept": "text/plain, */*",
                    "Referer": "https://finance.sina.com.cn/",
                    "User-Agent": "ChanQuant/0.2 local-research",
                },
                timeout=httpx.Timeout(connect=3.0, read=5.0, write=3.0, pool=3.0),
            )
        except httpx.HTTPError as error:
            raise SinaUpstreamError(f"Sina suggest request failed: {error}") from error
        if response.status_code != 200:
            raise SinaUpstreamError(f"Sina suggest request returned HTTP {response.status_code}")
        return _parse_suggestions(response.content, limit=limit)
    finally:
        if owns_client:
            http_client.close()


def fetch_sina_instrument(
    symbol: str,
    *,
    client: httpx.Client | None = None,
) -> InstrumentIdentity:
    canonical = symbol.strip().upper()
    match = re.fullmatch(r"(?P<code>\d{6})\.(?P<exchange>SZ|SH)", canonical)
    if match is None:
        raise SinaDataError("Sina sources support only NNNNNN.SZ or NNNNNN.SH")
    provider_symbol = f"{match.group('exchange').lower()}{match.group('code')}"
    items = search_sina_instruments(provider_symbol, limit=8, client=client)
    for item in items:
        if item.symbol == canonical:
            return item
    raise SinaDataError(f"Sina returned no instrument metadata for {canonical}")
