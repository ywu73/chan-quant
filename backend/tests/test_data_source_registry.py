from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from chan_quant.audit.data_source_registry import DataSourceRegistry, load_data_source_registry

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPOSITORY_ROOT / "docs" / "data-source-registry.json"


def test_repository_data_source_registry_is_valid_and_evidence_exists() -> None:
    registry = load_data_source_registry(REGISTRY_PATH)

    assert registry.schema_version == "data-source-registry-v0.1"
    assert all(
        (REPOSITORY_ROOT / evidence).is_file()
        for source in registry.sources
        for evidence in source.evidence_documents
    )


def test_registry_covers_active_market_inputs_and_tencent_candidates() -> None:
    registry = load_data_source_registry(REGISTRY_PATH)
    by_id = {source.source_id: source for source in registry.sources}

    assert {
        "user-csv-daily-bars",
        "auditable-market-snapshot",
        "sina-undocumented-kline",
        "sina-undocumented-quote",
        "sina-undocumented-batch-quote",
        "sina-undocumented-instrument-search",
        "sina-undocumented-market-breadth",
        "sse-official-universe",
        "szse-official-universe",
        "csi-official-index-membership",
        "tencent-undocumented-kline-candidate",
        "tencent-undocumented-quote-candidate",
    } <= set(by_id)
    assert by_id["tencent-undocumented-kline-candidate"].status == "CANDIDATE"
    assert by_id["tencent-undocumented-quote-candidate"].status == "CANDIDATE"
    assert by_id["tencent-undocumented-kline-candidate"].decisions.local_research == "NO_GO"
    assert by_id["tencent-undocumented-quote-candidate"].decisions.local_research == "NO_GO"
    assert by_id["tencent-undocumented-kline-candidate"].last_verified_at is not None
    assert by_id["tencent-undocumented-quote-candidate"].last_verified_at is not None
    assert by_id["tencent-undocumented-kline-candidate"].decisions.automatic_fallback == "NO_GO"
    assert by_id["tencent-undocumented-quote-candidate"].decisions.automatic_fallback == "NO_GO"
    batch_quote = by_id["sina-undocumented-batch-quote"]
    assert batch_quote.capability == "BATCH_QUOTE"
    assert batch_quote.decisions.local_research == "GO"
    assert batch_quote.decisions.production_market_data == "NO_GO"
    assert batch_quote.decisions.automatic_fallback == "NO_GO"


def test_registry_rejects_remote_sources_that_bypass_backend_controls() -> None:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    payload["sources"][0].update(
        {
            "remote": True,
            "backend_only": False,
            "remote_network_gate": False,
        }
    )

    with pytest.raises(ValidationError, match="remote sources must be backend-only"):
        DataSourceRegistry.model_validate(payload)


def test_registry_rejects_undocumented_source_as_production_go() -> None:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    source = next(
        item
        for item in payload["sources"]
        if item["source_id"] == "tencent-undocumented-kline-candidate"
    )
    source["decisions"]["production_market_data"] = "GO"

    with pytest.raises(ValidationError, match="undocumented sources must remain NO_GO"):
        DataSourceRegistry.model_validate(payload)


def test_registry_rejects_automatic_provider_fallback() -> None:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    payload["sources"][0]["decisions"]["automatic_fallback"] = "GO"

    with pytest.raises(ValidationError, match="forbids automatic provider fallback"):
        DataSourceRegistry.model_validate(payload)


def test_registry_does_not_treat_official_publication_as_usage_permission() -> None:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    source = next(
        item for item in payload["sources"] if item["source_id"] == "sse-official-universe"
    )
    source["decisions"]["commercial_use"] = "GO"

    with pytest.raises(ValidationError, match="unverified license status cannot be GO"):
        DataSourceRegistry.model_validate(payload)


def test_registry_review_must_follow_source_verification() -> None:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    payload["reviewed_at"] = "2026-08-05T22:00:00+08:00"

    with pytest.raises(ValidationError, match="reviewed_at cannot be earlier"):
        DataSourceRegistry.model_validate(payload)
