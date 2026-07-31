from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from chan_quant.domain.instrument import AssetType

Adjustment = Literal["qfq", "hfq", "unadjusted"]
AdjustmentBasis = Literal["provider-declared", "externally-audited"]


class MarketDataManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["market-snapshot-v0.1"]
    symbol: str
    instrument_name: str = Field(min_length=1, max_length=80)
    asset_type: AssetType = "UNKNOWN"
    price_precision: int = Field(default=2, ge=0, le=6)
    timeframe: Literal["1d"]
    provider: str = Field(min_length=1, max_length=80)
    adjustment: Adjustment
    adjustment_basis: AdjustmentBasis
    timezone: Literal["Asia/Shanghai"]
    fetched_at: datetime
    data_from: date
    data_to: date
    bar_count: int = Field(ge=1)
    bars_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    license_note: str = Field(min_length=1, max_length=240)
    audit_reference: str | None = Field(default=None, max_length=240)

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        canonical = value.strip().upper()
        if re.fullmatch(r"\d{6}\.(SZ|SH)", canonical) is None:
            raise ValueError("symbol must use canonical NNNNNN.SZ or NNNNNN.SH format")
        return canonical

    @field_validator("instrument_name", "provider", "license_note")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be blank")
        return normalized

    @field_validator("audit_reference")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("fetched_at")
    @classmethod
    def validate_fetched_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("fetched_at must include an explicit timezone offset")
        if value.utcoffset() != timedelta(hours=8):
            raise ValueError("fetched_at must use the Asia/Shanghai UTC+08:00 offset")
        return value

    @model_validator(mode="after")
    def validate_manifest_consistency(self) -> MarketDataManifest:
        if self.data_from > self.data_to:
            raise ValueError("expected data_from <= data_to")
        if self.data_to > self.fetched_at.date():
            raise ValueError("data_to cannot be later than fetched_at")
        if self.adjustment_basis == "externally-audited" and not self.audit_reference:
            raise ValueError("externally-audited adjustment requires audit_reference")
        return self


class DataQualityIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    severity: Literal["INFO", "WARNING", "DANGER"]
    message: str


class DataQualityRejection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["REJECTED"] = "REJECTED"
    code: str
    message: str


class DataQualityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["READY", "WARNING"]
    integrity: Literal["MATCH"]
    dataset_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    schema_version: Literal["market-snapshot-v0.1"]
    provider: str
    adjustment: Adjustment
    adjustment_basis: AdjustmentBasis
    timeframe: Literal["1d"]
    timezone: Literal["Asia/Shanghai"]
    fetched_at: datetime
    data_from: date
    data_to: date
    bar_count: int = Field(ge=1)
    bars_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    license_note: str
    audit_reference: str | None
    issues: list[DataQualityIssue]
