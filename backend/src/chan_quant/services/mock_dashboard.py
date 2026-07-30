"""Compatibility wrapper for the calculated synthetic dashboard."""

from chan_quant.domain.dashboard import DashboardSnapshot
from chan_quant.services.dashboard_builder import build_dashboard as _build_dashboard
from chan_quant.services.demo_market import build_demo_bars


def build_mock_dashboard(symbol: str = "DEMO.SZ") -> DashboardSnapshot:
    return _build_dashboard(
        build_demo_bars(),
        symbol=symbol,
        name="Independent v0.1 演示标的",
        is_mock=True,
        data_source="deterministic-synthetic",
        adjustment="not-applicable",
    )
