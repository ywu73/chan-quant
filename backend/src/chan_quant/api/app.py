import os
from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from chan_quant.data.csv_source import CsvDataError, load_csv_bars
from chan_quant.domain.dashboard import DashboardSnapshot
from chan_quant.services.dashboard_builder import build_dashboard
from chan_quant.services.demo_market import build_demo_bars

app = FastAPI(
    title="Chan Quant API",
    version="0.1.0",
    description="Auditable Independent v0.1 research API with synthetic or CSV market data.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "data_mode": "csv" if os.getenv("CHAN_QUANT_CSV_PATH") else "synthetic",
        "strategy": "independent-v0.1.0-draft",
    }


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
    csv_path = os.getenv("CHAN_QUANT_CSV_PATH")
    try:
        if csv_path:
            bars = load_csv_bars(csv_path)
            is_mock = False
            data_source = "csv"
            adjustment = os.getenv("CHAN_QUANT_ADJUSTMENT", "unspecified")
            name = os.getenv("CHAN_QUANT_INSTRUMENT_NAME", symbol.upper())
        else:
            bars = build_demo_bars()
            is_mock = True
            data_source = "deterministic-synthetic"
            adjustment = "not-applicable"
            name = "Independent v0.1 演示标的"

        if as_of is not None:
            bars = [bar for bar in bars if bar.date <= as_of]
        return build_dashboard(
            bars,
            symbol=symbol.upper(),
            name=name,
            is_mock=is_mock,
            data_source=data_source,
            adjustment=adjustment,
        )
    except (CsvDataError, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
