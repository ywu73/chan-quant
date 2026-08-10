import os
from datetime import date
from pathlib import Path
from typing import Annotated, Literal, cast

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from chan_quant import __version__
from chan_quant.data.csv_source import CsvDataError, load_csv_bars
from chan_quant.data.market_snapshot import MarketSnapshotError, load_market_snapshot
from chan_quant.data.remote_market_breadth import (
    RemoteMarketBreadthError,
    remote_market_breadth_service,
)
from chan_quant.data.sina_instrument_source import (
    fetch_sina_instrument,
    search_sina_instruments,
)
from chan_quant.data.sina_quote_source import (
    SinaQuoteUnavailableError,
    fetch_sina_quote,
    fetch_sina_quotes,
)
from chan_quant.data.sina_source import (
    SinaDataError,
    SinaUpstreamError,
    fetch_sina_kline_bars,
    to_sina_symbol,
)
from chan_quant.domain.comparison import ComparisonWarning, MarketComparison
from chan_quant.domain.dashboard import DashboardSnapshot
from chan_quant.domain.data_quality import DataQualityRejection, DataQualityReport
from chan_quant.domain.instrument import (
    InstrumentIdentity,
    InstrumentSearchResponse,
    MarketCode,
    normalize_canonical_symbol,
)
from chan_quant.domain.instrument_catalog import (
    InstrumentCatalogResponse,
    list_catalog_instruments,
    resolve_catalog_instrument,
)
from chan_quant.domain.market_breadth import MarketBreadthRejection, MarketBreadthSnapshot
from chan_quant.domain.quote import QuoteBatch, QuoteSnapshot
from chan_quant.runtime_config import (
    RuntimeConfigError,
    configured_data_mode,
    docs_enabled_for_startup,
    load_runtime_config,
    remote_network_enabled,
)
from chan_quant.services.dashboard_builder import build_dashboard
from chan_quant.services.demo_market import build_demo_bars
from chan_quant.services.market_comparison import (
    ComparisonInput,
    ComparisonLoadError,
    build_market_comparison,
)

router = APIRouter()

COMPARISON_MIN_SYMBOLS = 2
COMPARISON_MAX_SYMBOLS = 8
COMPARISON_MAX_WORKERS = 4
BATCH_QUOTE_MIN_SYMBOLS = 1
BATCH_QUOTE_MAX_SYMBOLS = 8

def _remote_network_enabled() -> bool:
    return remote_network_enabled()


def _require_remote_network() -> None:
    try:
        enabled = _remote_network_enabled()
    except ValueError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "REMOTE_NETWORK_CONFIGURATION_INVALID",
                "message": str(error),
            },
        ) from error
    if not enabled:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "REMOTE_NETWORK_DISABLED",
                "message": (
                    "remote market access is disabled by "
                    "CHAN_QUANT_REMOTE_NETWORK_ENABLED"
                ),
            },
        )


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


def _reject_unsupported_market_data(symbols: list[str], capability: str) -> None:
    unsupported: list[str] = []
    for symbol in symbols:
        try:
            _, market = normalize_canonical_symbol(symbol)
        except ValueError:
            continue
        if market not in {"CN", "SYNTHETIC"}:
            unsupported.append(symbol.strip().upper())
    if unsupported:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "REJECTED",
                "code": "MARKET_DATA_ADAPTER_UNAVAILABLE",
                "message": (
                    f"{capability} has no authorized provider adapter for "
                    f"{', '.join(unsupported)}"
                ),
            },
        )


def _configured_data_mode() -> Literal["synthetic", "csv", "sina", "snapshot"]:
    return configured_data_mode()


def _sina_datalen() -> int:
    raw = os.getenv("CHAN_QUANT_SINA_DATALEN", "2000")
    try:
        datalen = int(raw)
    except ValueError as error:
        raise ValueError("CHAN_QUANT_SINA_DATALEN must be an integer") from error
    if not 92 <= datalen <= 10_000:
        raise ValueError("CHAN_QUANT_SINA_DATALEN must be between 92 and 10000")
    return datalen


def _sina_comparison_input(symbol: str) -> ComparisonInput:
    try:
        bars = fetch_sina_kline_bars(symbol, datalen=_sina_datalen())
    except SinaUpstreamError as error:
        raise ComparisonLoadError("UPSTREAM_UNAVAILABLE", str(error)) from error
    except SinaDataError as error:
        raise ComparisonLoadError("DATA_UNAVAILABLE", str(error)) from error

    warnings: list[ComparisonWarning] = []
    try:
        instrument = fetch_sina_instrument(symbol)
        if instrument.asset_type == "ETF":
            adjustment = "unspecified"
            warnings.append(
                ComparisonWarning(
                    code="ETF_ADJUSTMENT_UNVERIFIED",
                    message=(
                        "该 ETF 的复权、分红与份额折算口径尚未完成审计；"
                        "归一化收益和回撤可能受到机械跳变影响。"
                    ),
                )
            )
        else:
            adjustment = "unadjusted-observed"
            warnings.append(
                ComparisonWarning(
                    code="DATA_SOURCE_ADJUSTMENT_UNCONTRACTED",
                    message=(
                        "新浪未提供固定复权口径合同；有限股票样本现场观测为不复权，"
                        "除权除息可能影响归一化收益和回撤。"
                    ),
                )
            )
    except (SinaDataError, SinaUpstreamError):
        instrument = _fallback_instrument(symbol, symbol)
        adjustment = "unspecified"
        warnings.append(
            ComparisonWarning(
                code="INSTRUMENT_METADATA_UNAVAILABLE",
                message="标的元数据与复权口径不可用，比较结果仅保留规范代码。",
            )
        )

    return ComparisonInput(
        instrument=instrument,
        bars=bars,
        data_source="sina-undocumented-kline",
        adjustment=adjustment,
        is_mock=False,
        warnings=warnings,
    )


@router.get("/health")
def health() -> dict[str, str]:
    status = "ok"
    try:
        data_mode = _configured_data_mode()
    except ValueError:
        data_mode = "invalid"
        status = "configuration_error"
    try:
        remote_network = "enabled" if _remote_network_enabled() else "disabled"
    except ValueError:
        remote_network = "invalid"
        status = "configuration_error"
    return {
        "status": status,
        "data_mode": data_mode,
        "remote_network": remote_network,
        "strategy": "independent-v0.1.0-draft",
    }


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "alive", "service": "chan-quant-api"}


def _path_is_readable_file(path: Path) -> bool:
    return path.is_file() and os.access(path, os.R_OK)


@router.get("/readyz")
def readyz() -> dict[str, str]:
    try:
        config = load_runtime_config()
    except RuntimeConfigError as error:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "RUNTIME_CONFIGURATION_INVALID",
                "message": str(error),
            },
        ) from error

    if config.data_mode == "csv":
        if not config.csv_path or not _path_is_readable_file(Path(config.csv_path)):
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "RUNTIME_DATA_PATH_UNAVAILABLE",
                    "message": "configured csv data path is not a readable file",
                },
            )
    elif config.data_mode == "snapshot":
        package = Path(config.snapshot_path) if config.snapshot_path else None
        required_files = ("manifest.json", "bars.csv")
        if package is None or any(
            not _path_is_readable_file(package / name) for name in required_files
        ):
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "RUNTIME_DATA_PATH_UNAVAILABLE",
                    "message": "configured snapshot package is not readable",
                },
            )

    return {"status": "ready", "service": "chan-quant-api"}


@router.get("/version")
def version() -> dict[str, str]:
    config = load_runtime_config()
    return {
        "application_version": __version__,
        "strategy_version": "independent-v0.1.0",
        "environment": config.environment,
        "release_sha": config.release_sha,
    }


@router.get("/api/v1/runtime-capabilities")
def runtime_capabilities() -> dict[str, str | bool]:
    config = load_runtime_config()
    return {
        "data_mode": config.data_mode,
        "remote_network_enabled": config.remote_network_enabled,
        "force_refresh_enabled": config.force_refresh_enabled,
        "research_preview": config.research_preview,
        "release_sha": config.release_sha,
    }


@router.get(
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
    _require_remote_network()
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


@router.get(
    "/api/v1/instruments/catalog",
    response_model=InstrumentCatalogResponse,
)
def instrument_catalog(market: MarketCode | None = None) -> InstrumentCatalogResponse:
    return InstrumentCatalogResponse(items=list_catalog_instruments(market))


@router.get(
    "/api/v1/instruments/{symbol}",
    response_model=InstrumentIdentity,
)
def instrument_identity(symbol: str) -> InstrumentIdentity:
    catalog_entry = resolve_catalog_instrument(symbol)
    if catalog_entry is not None:
        return catalog_entry.instrument
    try:
        _, market = normalize_canonical_symbol(symbol)
    except ValueError:
        market = None
    if market in {"HK", "US", "GLOBAL"}:
        raise HTTPException(
            status_code=422,
            detail={
                "status": "REJECTED",
                "code": "IDENTITY_NOT_IN_AUDITED_CATALOG",
                "message": f"no audited instrument identity is available for {symbol.upper()}",
            },
        )
    _require_remote_network()
    try:
        return fetch_sina_instrument(symbol)
    except SinaUpstreamError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except SinaDataError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/api/v1/market-comparison",
    response_model=MarketComparison,
)
def market_comparison(
    symbols: Annotated[list[str], Query()],
    start: date | None = None,
    end: date | None = None,
) -> MarketComparison:
    canonical_symbols = [symbol.strip().upper() for symbol in symbols]
    if not COMPARISON_MIN_SYMBOLS <= len(canonical_symbols) <= COMPARISON_MAX_SYMBOLS:
        raise HTTPException(status_code=422, detail="comparison requires 2 to 8 symbols")
    if len(set(canonical_symbols)) != len(canonical_symbols):
        raise HTTPException(status_code=422, detail="comparison symbols must be distinct")
    _reject_unsupported_market_data(canonical_symbols, "daily comparison")
    _require_remote_network()
    try:
        for symbol in canonical_symbols:
            to_sina_symbol(symbol)
        if _configured_data_mode() != "sina":
            raise ValueError(
                "multi-symbol comparison currently requires CHAN_QUANT_DATA_SOURCE=sina; "
                "single CSV and snapshot packages cannot represent multiple instruments"
            )
        return build_market_comparison(
            canonical_symbols,
            _sina_comparison_input,
            start=start,
            end=end,
            max_workers=COMPARISON_MAX_WORKERS,
        )
    except (SinaDataError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/api/v1/quotes",
    response_model=QuoteBatch,
)
def quote_batch(symbols: Annotated[list[str] | None, Query()] = None) -> QuoteBatch:
    canonical_symbols = [symbol.strip().upper() for symbol in symbols or []]
    if not BATCH_QUOTE_MIN_SYMBOLS <= len(canonical_symbols) <= BATCH_QUOTE_MAX_SYMBOLS:
        raise HTTPException(status_code=422, detail="batch quote requires 1 to 8 symbols")
    if len(set(canonical_symbols)) != len(canonical_symbols):
        raise HTTPException(status_code=422, detail="batch quote symbols must be distinct")
    _reject_unsupported_market_data(canonical_symbols, "quote")
    _require_remote_network()
    try:
        return fetch_sina_quotes(canonical_symbols)
    except SinaUpstreamError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except SinaDataError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/api/v1/instruments/{symbol}/quote",
    response_model=QuoteSnapshot,
)
def quote(symbol: str) -> QuoteSnapshot:
    _reject_unsupported_market_data([symbol], "quote")
    _require_remote_network()
    try:
        return fetch_sina_quote(symbol)
    except SinaQuoteUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except SinaUpstreamError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except SinaDataError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.get(
    "/api/v1/market-breadth",
    response_model=MarketBreadthSnapshot,
)
def market_breadth(
    market: str = Query(default="CN_A_SH_SZ_V1"),
    refresh: bool = Query(default=False),
) -> MarketBreadthSnapshot:
    if market != "CN_A_SH_SZ_V1":
        rejection = MarketBreadthRejection(
            code="MARKET_UNSUPPORTED",
            message="market must be CN_A_SH_SZ_V1",
        )
        raise HTTPException(status_code=422, detail=rejection.model_dump())
    if refresh:
        try:
            force_refresh_enabled = load_runtime_config().force_refresh_enabled
        except RuntimeConfigError as error:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "RUNTIME_CONFIGURATION_INVALID",
                    "message": str(error),
                },
            ) from error
        if not force_refresh_enabled:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "FORCE_REFRESH_DISABLED",
                    "message": "forced market breadth refresh is disabled by runtime policy",
                },
            )
    _require_remote_network()
    try:
        return remote_market_breadth_service.get(force_refresh=refresh)
    except RemoteMarketBreadthError as error:
        rejection = MarketBreadthRejection(code=error.code, message=error.message)
        raise HTTPException(status_code=502, detail=rejection.model_dump()) from error


@router.get(
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
    _reject_unsupported_market_data([symbol], "dashboard daily bars")
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
            _require_remote_network()
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


def create_app() -> FastAPI:
    try:
        docs_enabled = docs_enabled_for_startup()
    except RuntimeConfigError:
        docs_enabled = False

    application = FastAPI(
        title="Chan Quant API",
        version=__version__,
        description=(
            "Auditable Independent v0.1 research API with synthetic, CSV, immutable "
            "local snapshots, or undocumented Sina K-line data."
        ),
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    try:
        config = load_runtime_config()
        allowed_hosts = list(config.allowed_hosts)
        environment = config.environment
    except RuntimeConfigError:
        allowed_hosts = ["localhost", "127.0.0.1", "testserver"]
        environment = os.getenv("CHAN_QUANT_ENVIRONMENT", "development").strip().lower()

    if environment != "production":
        application.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
            allow_credentials=False,
            allow_methods=["GET"],
            allow_headers=["*"],
        )
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
    application.include_router(router)
    return application


app = create_app()
