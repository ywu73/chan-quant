from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AssetType = Literal["ETF", "UNKNOWN"]


class InstrumentIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    name: str
    exchange: Literal["SZ", "SH"] | None
    asset_type: AssetType
    price_precision: int = Field(ge=0, le=6)


class InstrumentSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    items: list[InstrumentIdentity]
    source: Literal["sina-undocumented-suggest"] = "sina-undocumented-suggest"
    limit: int = Field(ge=1, le=20)
