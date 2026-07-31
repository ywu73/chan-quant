import os
from datetime import date
from typing import Literal, cast

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from chan_quant.data.csv_source import CsvDataError, load_csv_bars
from chan_quant.data.market_snapshot import MarketSnapshotError, load_market_snapshot
from chan_quant.data.sina_instrument_source import (
    fetch_sina_instrument,
    search_sina_instruments,
)
from chan_quant.data.sina_quote_source import SinaQuoteUnavailableError, fetch_sina_quote
from chan_quant.data.sina_source import (
    SinaDataError,
    SinaUpstreamError,
    fetch_sina_kline_bars,
)
from chan_quant.domain.dashboard import DashboardSnapshot
from chan_quant.domain.data_quality import DataQualityRejection, DataQualityReport
from chan_quant.domain.instrument import InstrumentIdentity, InstrumentSearchResponse
from chan_quant.domain.quote import QuoteSnapshot
from chan_quant.services.dashboard_builder import build_dashboard
from chan_quant.services.demo_market import build_demo_bars

app = FastAPI(
    title="Chan Quant API",
    version="0.1.0",
    description=(
        "Auditable Independent v0.1 research API with synthetic, CSV, immutable "
        "local snapshots, or undocumented Sina K-line data."
    ),
)

DataMode = Literal["synthetic", "csv", "sina", "snapshot"]


def _fallback_instrument(symbol: str, name: str) -> InstrumentIdentity:
    canonical = symbol.strip().upper()
    exchange = canonical.rsplit(".", 1)[-1] if "." in canonical else None
    if exchange not in {"SZ", "SH"}:
        exchange = None
    return InstrumentIdentity(
        symbol=canonical,
        name=name,
        exchange=cast(Literal["SZ", "SH"] | None, exchange),
        asset_type="UNKNOWN",
        price_precision=2,
    )


def _configured_data_mode() -> DataMode:
    configured = os.getenv("CHAN_QUANT_DATA_SOURCE", "").strip().lower()
    if not configured:
        if os.getenv("CHAN_QUANT_DATA_PACKAGE_PATH"):
            return "snapshot"
        return "csv" if os.getenv("CHAN_QUANT_CSV_PATH") else "synthetic"
    if configured not in {"synthetic", "csv", "sina", "snapshot"}:
        raise ValueError("CHAN_QUANT_DATA_SOURCE must be synthetic, csv, sina, or snapshot")
    return cast(DataMode, configured)


def _sina_datalen() -> int:
    raw = os.getenv("CHAN_QUANT_SINA_DATALEN", "2000")
    try:
        datalen = int(raw)
    except ValueError as error:
        raise ValueError("CHAN_QUANT_SINA_DATALEN must be an integer") from error
    if not 92 <= datalen <= 10_000:
        raise ValueError("CHAN_QUANT_SINA_DATALEN must be between 92 and 10000")
    return datalen


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    try:
        data_mode = _configured_data_mode()
        status = "ok"
    except ValueError:
        data_mode = "invalid"
        status = "configuration_error"
    return {
        "status": status,
        "data_mode": data_mode,
        "strategy": "independent-v0.1.0-draft",
    }


@app.get(
    "/api/v1/instruments/search",
    response_model=InstrumentSearchResponse,
)
def instrument_search(
    q: str = Query(min_length=1, max_length=40),
    limit: int = Query(default=8, ge=1, le=20),
) -> InstrumentSearchResponse:
    normalized_query = q.strip()
    if not normalized_query:
        raise HTTPException(status_code=422, detail="instrument search query must not be empty")
    try:
        items = search_sina_instruments(normalized_query, limit=limit)
        return InstrumentSearchResponse(
            query=normalized_query,
            items=items,
            limit=limit,
        )
    except SinaUpstreamError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except SinaDataError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get(
    "/api/v1/instruments/{symbol}/quote",
    response_model=QuoteSnapshot,
)
def quote(symbol: str) -> QuoteSnapshot:
    try:
        return fetch_sina_quote(symbol)
    except SinaQuoteUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except SinaUpstreamError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except SinaDataError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get(
    "/api/v1/instruments/{symbol}/dashboard",
    response_model=DashboardSnapshot,
)
def dashboard(
    symbol: str,
    timeframe: str = Query(default="1d", pattern="^(1d)$"),
    as_of: date | None = None,
    lookback: str = Query(default="2y", pattern="^(2y)$"),
) -> DashboardSnapshot:
    del timeframe, lookback
    try:
        data_mode = _configured_data_mode()
        data_quality: DataQualityReport | None = None
        if data_mode == "snapshot":
            package_path = os.getenv("CHAN_QUANT_DATA_PACKAGE_PATH")
            if not package_path:
                raise ValueError("CHAN_QUANT_DATA_PACKAGE_PATH is required in snapshot mode")
            loaded = load_market_snapshot(package_path, expected_symbol=symbol)
            bars = loaded.bars
            manifest = loaded.manifest
            is_mock = False
            data_source = "auditable-market-snapshot"
            adjustment = manifest.adjustment
            exchange = manifest.symbol.rsplit(".", 1)[1]
            instrument = InstrumentIdentity(
                symbol=manifest.symbol,
                name=manifest.instrument_name,
                exchange=cast(Literal["SZ", "SH"], exchange),
                asset_type=manifest.asset_type,
                price_precision=manifest.price_precision,
            )
            data_quality = loaded.quality
        elif data_mode == "csv":
            csv_path = os.getenv("CHAN_QUANT_CSV_PATH")
            if not csv_path:
                raise ValueError("CHAN_QUANT_CSV_PATH is required in csv mode")
            bars = load_csv_bars(csv_path)
            is_mock = False
            data_source = "csv"
            adjustment = os.getenv("CHAN_QUANT_ADJUSTMENT", "unspecified")
            name = os.getenv("CHAN_QUANT_INSTRUMENT_NAME", symbol.upper())
            instrument = _fallback_instrument(symbol, name)
        elif data_mode == "sina":
            bars = fetch_sina_kline_bars(symbol, datalen=_sina_datalen())
            is_mock = False
            data_source = "sina-undocumented-kline"
            try:
                instrument = fetch_sina_instrument(symbol)
                adjustment = (
                    "unspecified" if instrument.asset_type == "ETF" else "unadjusted-observed"
                )
            except (SinaDataError, SinaUpstreamError):
                # Instrument metadata must never make an otherwise valid research
                # snapshot unavailable. A canonical symbol is safer than a stale
                # or globally configured name belonging to another instrument.
                instrument = _fallback_instrument(symbol, symbol.upper())
                adjustment = "unspecified"
        else:
            bars = build_demo_bars()
            is_mock = True
            data_source = "deterministic-synthetic"
            adjustment = "not-applicable"
            instrument = _fallback_instrument(symbol, "Independent v0.1 演示标的")

        if as_of is not None:
            bars = [bar for bar in bars if bar.date <= as_of]
        return build_dashboard(
            bars,
            instrument=instrument,
            is_mock=is_mock,
            data_source=data_source,
            adjustment=adjustment,
            data_quality=data_quality,
        )
    except SinaUpstreamError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except MarketSnapshotError as error:
        rejection = DataQualityRejection(code=error.code, message=error.message)
        raise HTTPException(status_code=422, detail=rejection.model_dump()) from error
    except (CsvDataError, SinaDataError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
