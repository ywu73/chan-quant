from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SourceStatus = Literal["ACTIVE_RESEARCH", "CANDIDATE", "OFFLINE_ONLY"]
SourceCapability = Literal[
    "DAILY_BARS",
    "QUOTE",
    "INSTRUMENT_SEARCH",
    "MARKET_BREADTH_QUOTES",
    "UNIVERSE",
    "INDEX_MEMBERSHIP",
]
ContractStatus = Literal[
    "PROJECT_OWNED",
    "USER_DECLARED",
    "OFFICIAL_PRIMARY_SOURCE",
    "UNDOCUMENTED_OBSERVED",
]
LicenseStatus = Literal["PROJECT_OWNED", "USER_RESPONSIBLE", "UNVERIFIED"]
Decision = Literal["GO", "CONDITIONAL_GO", "NO_GO", "PENDING", "NOT_APPLICABLE"]
Market = Literal["CN_SH", "CN_SZ"]
Adjustment = Literal["NONE", "QFQ", "HFQ", "UNADJUSTED_OBSERVED", "UNSPECIFIED"]


class SourceDecisions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_research: Decision
    production_market_data: Decision
    commercial_use: Decision
    redistribution: Decision
    automatic_fallback: Decision


class DataSourceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    provider: str = Field(min_length=1, max_length=80)
    capability: SourceCapability
    status: SourceStatus
    contract_status: ContractStatus
    license_status: LicenseStatus
    remote: bool
    backend_only: bool
    remote_network_gate: bool
    markets: list[Market]
    adjustments: list[Adjustment]
    last_verified_at: datetime | None
    evidence_documents: list[str] = Field(min_length=1)
    decisions: SourceDecisions
    known_limitations: list[str] = Field(min_length=1)

    @field_validator("provider")
    @classmethod
    def strip_provider(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("provider must not be blank")
        return normalized

    @field_validator("markets", "adjustments", "evidence_documents", "known_limitations")
    @classmethod
    def reject_duplicates(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("registry lists must not contain duplicates")
        return value

    @field_validator("evidence_documents")
    @classmethod
    def validate_evidence_paths(cls, value: list[str]) -> list[str]:
        for path in value:
            if re.fullmatch(r"docs/[a-z0-9][a-z0-9-]*\.md", path) is None:
                raise ValueError("evidence documents must be repository-relative docs/*.md paths")
        return value

    @field_validator("last_verified_at")
    @classmethod
    def validate_verification_time(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("last_verified_at must include an explicit timezone offset")
        if value.utcoffset() != timedelta(hours=8):
            raise ValueError("last_verified_at must use the Asia/Shanghai UTC+08:00 offset")
        return value

    @model_validator(mode="after")
    def validate_policy(self) -> DataSourceRecord:
        if self.remote and (not self.backend_only or not self.remote_network_gate):
            raise ValueError("remote sources must be backend-only and use the remote network gate")
        if not self.remote and self.remote_network_gate:
            raise ValueError("local sources must not claim the remote network gate")
        if self.contract_status == "UNDOCUMENTED_OBSERVED":
            if self.license_status != "UNVERIFIED":
                raise ValueError("undocumented sources must retain an unverified license status")
            for decision in (
                self.decisions.production_market_data,
                self.decisions.commercial_use,
                self.decisions.redistribution,
            ):
                if decision != "NO_GO":
                    raise ValueError(
                        "undocumented sources must remain NO_GO for production, commercial use, "
                        "and redistribution"
                    )
        if self.license_status == "UNVERIFIED":
            for decision in (
                self.decisions.production_market_data,
                self.decisions.commercial_use,
                self.decisions.redistribution,
            ):
                if decision == "GO":
                    raise ValueError(
                        "unverified license status cannot be GO for production, commercial use, "
                        "or redistribution"
                    )
        if self.status == "CANDIDATE" and self.decisions.production_market_data == "GO":
            raise ValueError("candidate sources cannot be production GO")
        if self.decisions.automatic_fallback != "NO_GO":
            raise ValueError("registry v0.1 forbids automatic provider fallback")
        if self.capability == "DAILY_BARS" and not self.adjustments:
            raise ValueError("daily bar sources must declare adjustment semantics")
        if self.capability != "DAILY_BARS" and self.adjustments:
            raise ValueError("only daily bar sources may declare adjustments")
        return self


class DataSourceRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["data-source-registry-v0.1"]
    scope: Literal["external-and-user-supplied-market-inputs"]
    reviewed_at: datetime
    sources: list[DataSourceRecord] = Field(min_length=1)

    @field_validator("reviewed_at")
    @classmethod
    def validate_reviewed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timedelta(hours=8):
            raise ValueError("reviewed_at must use the Asia/Shanghai UTC+08:00 offset")
        return value

    @model_validator(mode="after")
    def validate_unique_sources(self) -> DataSourceRegistry:
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source_id values must be unique")
        if any(
            source.last_verified_at is not None and source.last_verified_at > self.reviewed_at
            for source in self.sources
        ):
            raise ValueError("reviewed_at cannot be earlier than a source verification time")
        return self


def load_data_source_registry(path: str | Path) -> DataSourceRegistry:
    registry_path = Path(path)
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"data source registry could not be read: {error}") from error
    return DataSourceRegistry.model_validate(payload)
