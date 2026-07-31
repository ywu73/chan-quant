from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

QuoteStatus = Literal["LIVE", "DELAYED", "CLOSED"]


class QuoteSnapshot(BaseModel):
    """A point-in-time quote that is isolated from daily strategy inputs."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    name: str
    last_price: float
    previous_close: float
    change: float
    change_percent: float
    open: float
    high: float
    low: float
    volume: int
    quote_at: datetime
    received_at: datetime
    source: Literal["sina-undocumented-quote"] = "sina-undocumented-quote"
    status: QuoteStatus
    is_stale: bool
