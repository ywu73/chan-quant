from datetime import date

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from chan_quant.domain.dashboard import DashboardSnapshot
from chan_quant.services.mock_dashboard import build_mock_dashboard

app = FastAPI(
    title="Chan Quant API",
    version="0.1.0",
    description="Auditable quantitative research API. Current dashboard data is mock-only.",
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
    return {"status": "ok", "data_mode": "mock"}


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
    del timeframe, as_of, lookback
    return build_mock_dashboard(symbol=symbol.upper())
