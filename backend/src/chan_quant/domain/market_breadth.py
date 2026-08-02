from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

MarketBreadthStatus = Literal["COMPLETE", "PARTIAL", "FAILED"]
UnavailableReason = Literal[
    "SUSPENDED",
    "NO_TRADE_YET",
    "MISSING_QUOTE",
    "INVALID_PRICE",
    "NO_REFERENCE_PRICE",
]


class BreadthUniverseMember(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    exchange: Literal["SH", "SZ"]
    security_name: str = Field(min_length=1)
    security_type: Literal["A_STOCK"]
    board: Literal["MAIN", "STAR", "CHINEXT"]
    list_date: date
    delist_date: date | None = None

    @model_validator(mode="after")
    def validate_board_exchange(self) -> BreadthUniverseMember:
        if self.board == "STAR" and self.exchange != "SH":
            raise ValueError("STAR members must use exchange SH")
        if self.board == "CHINEXT" and self.exchange != "SZ":
            raise ValueError("CHINEXT members must use exchange SZ")
        return self


class BreadthObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    session_date: date
    previous_close: Decimal | None = None
    last_price: Decimal | None = None
    unavailable_reason: UnavailableReason | None = None
    provider_change_percent: Decimal | None = None

    @model_validator(mode="after")
    def validate_availability_shape(self) -> BreadthObservation:
        if self.unavailable_reason is not None and (
            self.previous_close is not None or self.last_price is not None
        ):
            raise ValueError("unavailable observations must not contain prices")
        return self


class MarketBreadthBuildInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    market: Literal["CN_A_SH_SZ_V1"]
    mode: Literal["EOD", "OBSERVED"]
    session_date: date
    universe_id: str
    universe_as_of: date
    snapshot_at: datetime
    received_at: datetime
    source: str
    dataset_id: str
    quality_policy_version: Literal["market-breadth-quality-v0.1"]
    calculation_policy_version: Literal["market-breadth-calculation-v0.1"]
    universe_members: list[BreadthUniverseMember]
    observations: list[BreadthObservation]


class MarketBreadthBin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Literal[
        "lt_m7",
        "m7_m5",
        "m5_m3",
        "m3_m2",
        "m2_m1",
        "m1_0",
        "p0_p1",
        "p1_p2",
        "p2_p3",
        "p3_p5",
        "p5_p7",
        "gt_p7",
    ]
    label: str
    side: Literal["DECLINE", "ADVANCE"]
    count: int = Field(ge=0)


class MarketBreadthIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: Literal["INFO", "WARNING", "DANGER"]
    message: str


class MarketBreadthSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: MarketBreadthStatus
    market: Literal["CN_A_SH_SZ_V1"]
    mode: Literal["EOD", "OBSERVED"]
    session_date: date
    universe_id: str
    universe_as_of: date
    snapshot_at: datetime
    received_at: datetime
    source: str
    dataset_id: str
    quality_policy_version: str
    calculation_policy_version: str
    universe_total: int = Field(ge=0)
    covered: int = Field(ge=0)
    unavailable: int = Field(ge=0)
    explicitly_unavailable: int = Field(ge=0)
    coverage_ratio: Decimal = Field(ge=0, le=1)
    resolution_ratio: Decimal = Field(ge=0, le=1)
    advancers: int = Field(ge=0)
    decliners: int = Field(ge=0)
    unchanged: int = Field(ge=0)
    bins: list[MarketBreadthBin]
    unavailable_reasons: dict[str, int]
    issues: list[MarketBreadthIssue]

    @field_serializer("coverage_ratio", "resolution_ratio", when_used="json")
    def serialize_ratio(self, value: Decimal) -> float:
        return float(value)


class MarketBreadthRejection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["REJECTED"] = "REJECTED"
    code: str
    message: str
