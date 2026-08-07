from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from mcp_server.client import ChanQuantClient
    from mcp_server.errors import ChanQuantError
else:
    from .client import ChanQuantClient
    from .errors import ChanQuantError


PLUGIN_VERSION = "0.2.0"
MIN_HISTORY_BARS = 92


def envelope(
    status: str,
    code: str,
    message: str,
    data: Any = None,
    *,
    warnings: list[str] | None = None,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "code": code,
        "message": message,
        "data": data,
        "warnings": warnings or [],
        "provenance": {
            "plugin_version": PLUGIN_VERSION,
            "data_source": None,
            "data_mode": None,
            "strategy_version": "independent-v0.1.0-draft",
            "parameter_version": None,
            **(provenance or {}),
        },
    }


def _error(error: ChanQuantError) -> dict[str, Any]:
    return envelope(error.status, error.code, error.message)


def _client() -> ChanQuantClient:
    return ChanQuantClient()


def get_runtime_status(_: dict[str, Any]) -> dict[str, Any]:
    try:
        client = _client()
        health = client.health()
        return envelope(
            "OK" if health["status"] == "ok" else "PARTIAL",
            "RUNTIME_AVAILABLE" if health["status"] == "ok" else "RUNTIME_CONFIGURATION_ERROR",
            "Chan Quant local API is reachable.",
            {
                "api_base": client.api_base,
                "ui_base": client.ui_base,
                "navigation_urls": {
                    "market_overview": client.url("/"),
                    "instrument_search": client.url("/search"),
                    "comparison": client.url("/compare"),
                    "indices": client.url("/indices"),
                    "methodology": client.url("/methodology"),
                },
                **health,
            },
            provenance={"data_mode": health["data_mode"], "data_source": "chan-quant-health"},
        )
    except ChanQuantError as error:
        return _error(error)


def resolve_instruments(arguments: dict[str, Any]) -> dict[str, Any]:
    query = arguments.get("query")
    limit = arguments.get("limit", 8)
    if not isinstance(query, str) or not query.strip():
        return envelope("REJECTED", "INVALID_QUERY", "query must be a non-empty string")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
        return envelope("REJECTED", "INVALID_LIMIT", "limit must be an integer from 1 to 20")
    try:
        client = _client()
        data = client.get("/api/v1/instruments/search", {"q": query.strip(), "limit": limit})
        return envelope(
            "OK", "INSTRUMENTS_RESOLVED", "Instrument candidates resolved.", data,
            warnings=["Search uses the backend's undocumented provider adapter."],
            provenance={"data_source": "sina-undocumented-instrument-search", "data_mode": "remote"},
        )
    except ChanQuantError as error:
        return _error(error)


def _parallel(fetchers: dict[str, Callable[[], Any]]) -> dict[str, Any]:
    with ThreadPoolExecutor(max_workers=len(fetchers)) as executor:
        futures = {key: executor.submit(fetch) for key, fetch in fetchers.items()}
        outcomes: dict[str, Any] = {}
        for key, future in futures.items():
            try:
                outcomes[key] = future.result()
            except ChanQuantError as error:
                outcomes[key] = _error(error)
            except (OSError, RuntimeError, TypeError, ValueError) as error:
                outcomes[key] = envelope("UNAVAILABLE", "ADAPTER_FAILURE", str(error))
        return outcomes


def inspect_instrument(arguments: dict[str, Any]) -> dict[str, Any]:
    symbol = arguments.get("symbol")
    as_of = arguments.get("as_of")
    if not isinstance(symbol, str) or not symbol.strip():
        return envelope("REJECTED", "INVALID_SYMBOL", "symbol must be a non-empty string")
    if as_of is not None:
        try:
            date.fromisoformat(as_of)
        except (TypeError, ValueError):
            return envelope("REJECTED", "INVALID_AS_OF", "as_of must be an ISO date")
    canonical = symbol.strip().upper()
    client = None
    try:
        client = _client()
        query = {"as_of": as_of} if as_of else None
        outcomes = _parallel({
            "daily_model": lambda: client.get(f"/api/v1/instruments/{canonical}/dashboard", query),
            "quote": lambda: client.get(f"/api/v1/instruments/{canonical}/quote"),
        })
    except ChanQuantError as error:
        return _error(error)
    dashboard = outcomes["daily_model"]
    quote = outcomes["quote"]
    dashboard_ok = not (isinstance(dashboard, dict) and "status" in dashboard and "code" in dashboard and "data" in dashboard)
    quote_ok = not (isinstance(quote, dict) and "status" in quote and "code" in quote and "data" in quote)
    if not dashboard_ok and not quote_ok:
        return envelope("UNAVAILABLE", "INSTRUMENT_RESEARCH_UNAVAILABLE", "daily model and independent quote are unavailable.", {"daily_model": dashboard, "quote": quote})
    data = {
        "symbol": canonical,
        "daily_model": dashboard if dashboard_ok else None,
        "quote": quote if quote_ok else None,
        "daily_model_url": client.url(f"/?symbol={canonical}"),
        "dashboard_url": client.url("/", {"symbol": canonical}),
        "quote_error": None if quote_ok else quote,
        "daily_model_error": None if dashboard_ok else dashboard,
    }
    status = "OK" if dashboard_ok and quote_ok else "PARTIAL"
    warnings = ["日线模型和独立实时 Quote 分开读取；Quote 不会重算已确认的日线策略。"]
    if not quote_ok:
        warnings.append("独立 Quote 不可用，未使用旧缓存、合成数据或其他来源回退。")
    return envelope(status, "INSTRUMENT_RESEARCH_READY" if status == "OK" else "INSTRUMENT_RESEARCH_PARTIAL", "Instrument research assembled.", data, warnings=warnings, provenance={"data_source": "chan-quant-backend", "data_mode": "backend-configured"})


def compare_instruments(arguments: dict[str, Any]) -> dict[str, Any]:
    symbols = arguments.get("symbols")
    if not isinstance(symbols, list) or not 2 <= len(symbols) <= 8 or any(not isinstance(item, str) or not item.strip() for item in symbols):
        return envelope("REJECTED", "INVALID_SYMBOLS", "symbols must contain 2 to 8 non-empty strings")
    canonical = [item.strip().upper() for item in symbols]
    if len(set(canonical)) != len(canonical):
        return envelope("REJECTED", "DUPLICATE_SYMBOLS", "symbols must be distinct")
    params: dict[str, Any] = {"symbols": canonical}
    for key in ("start", "end"):
        value = arguments.get(key)
        if value is not None:
            try:
                date.fromisoformat(value)
            except (TypeError, ValueError):
                return envelope("REJECTED", f"INVALID_{key.upper()}", f"{key} must be an ISO date")
            params[key] = value
    try:
        client = _client()
        outcomes = _parallel({
            "comparison": lambda: client.get("/api/v1/market-comparison", params),
            "quotes": lambda: client.get("/api/v1/quotes", {"symbols": canonical}),
        })
    except ChanQuantError as error:
        return _error(error)
    comparison = outcomes["comparison"]
    quotes = outcomes["quotes"]
    comparison_ok = not (isinstance(comparison, dict) and "status" in comparison and "code" in comparison and "data" in comparison)
    quotes_ok = not (isinstance(quotes, dict) and "status" in quotes and "code" in quotes and "data" in quotes)
    if not comparison_ok and not quotes_ok:
        return envelope("UNAVAILABLE", "COMPARISON_UNAVAILABLE", "comparison and independent quotes are unavailable.", {"comparison": comparison, "quotes": quotes})
    domain_status = comparison.get("status") if comparison_ok and isinstance(comparison, dict) else "FAILED"
    status = "OK" if comparison_ok and quotes_ok and domain_status == "COMPLETE" else "PARTIAL"
    data = {
        "comparison": comparison if comparison_ok else None,
        "quotes": quotes if quotes_ok else None,
        "comparison_url": client.url("/compare", {"symbols": ",".join(canonical)}),
        "quote_error": None if quotes_ok else quotes,
        "comparison_error": None if comparison_ok else comparison,
    }
    return envelope(status, f"COMPARISON_{domain_status}", "Comparison assembled without forward filling or FX conversion.", data, warnings=["Historical comparison and current Quote are separate observations.", "内置观察组如被使用，只代表版本化观察集合，不是官方指数或官方加权组合。"], provenance={"data_source": "chan-quant-backend", "data_mode": "backend-configured"})


def inspect_market_breadth(arguments: dict[str, Any]) -> dict[str, Any]:
    refresh = arguments.get("refresh", False)
    if not isinstance(refresh, bool):
        return envelope("REJECTED", "INVALID_REFRESH", "refresh must be boolean")
    try:
        client = _client()
        data = client.get("/api/v1/market-breadth", {"refresh": refresh})
        status = data.get("status") if isinstance(data, dict) else "FAILED"
        return envelope(
            "OK" if status == "COMPLETE" else "PARTIAL",
            f"MARKET_BREADTH_{status}",
            "A-share market breadth observation loaded.",
            data,
            warnings=["远程市场温度是现场观测，不是可审计快照；新浪来源未文档化。", "refresh=true 会重新读取全部远程输入，可能失败且不回退旧缓存。"],
            provenance={"data_source": "sina-undocumented-market-breadth", "data_mode": "observed"},
        )
    except ChanQuantError as error:
        return _error(error)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        return list(reader), fields


def _audit_bars(rows: list[dict[str, str]], fields: list[str]) -> dict[str, Any]:
    required = {"date", "open", "high", "low", "close", "volume"}
    missing = sorted(required.difference(fields))
    issues: list[dict[str, str]] = []
    dates: list[date] = []
    valid = 0
    if missing:
        issues.append({"code": "SCHEMA_MISSING_COLUMNS", "severity": "DANGER", "message": ", ".join(missing)})
    for index, row in enumerate(rows, start=2):
        try:
            current = date.fromisoformat(row["date"])
            values = [float(row[key]) for key in ("open", "high", "low", "close")]
            volume = int(row["volume"])
            if min(values) <= 0 or volume < 0 or values[2] > min(values[0], values[3]) or values[1] < max(values[0], values[3]):
                raise ValueError("OHLCV bounds are invalid")
            dates.append(current)
            valid += 1
        except (KeyError, TypeError, ValueError) as error:
            issues.append({"code": "ROW_INVALID", "severity": "DANGER", "message": f"row {index}: {error}"})
    if len(dates) != len(set(dates)):
        issues.append({"code": "DUPLICATE_DATES", "severity": "DANGER", "message": "date values must be unique"})
    if valid < MIN_HISTORY_BARS:
        issues.append({"code": "INSUFFICIENT_HISTORY", "severity": "WARNING", "message": f"at least {MIN_HISTORY_BARS} valid daily bars are required"})
    return {
        "fields": fields,
        "required_fields": sorted(required),
        "valid_rows": valid,
        "date_from": min(dates).isoformat() if dates else None,
        "date_to": max(dates).isoformat() if dates else None,
        "frequency": "1d (declared by input contract)",
        "timezone": "unspecified unless snapshot manifest declares it",
        "issues": issues,
        "status": "READY" if not any(item["severity"] == "DANGER" for item in issues) and valid >= MIN_HISTORY_BARS else "REJECTED",
    }


def _audit_snapshot(root: Path, expected_symbol: str | None) -> dict[str, Any]:
    manifest_path = root / "manifest.json"
    bars_path = root / "bars.csv"
    if not manifest_path.is_file():
        return {"status": "REJECTED", "code": "MANIFEST_MISSING", "message": "manifest.json is missing"}
    if not bars_path.is_file():
        return {"status": "REJECTED", "code": "BARS_MISSING", "message": "bars.csv is missing"}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return {"status": "REJECTED", "code": "MANIFEST_INVALID", "message": str(error)}
    actual = _sha256(bars_path)
    expected = manifest.get("bars_sha256") if isinstance(manifest, dict) else None
    if actual != expected:
        return {"status": "REJECTED", "code": "HASH_MISMATCH", "message": "bars.csv SHA-256 does not match manifest"}
    if expected_symbol and manifest.get("symbol") != expected_symbol.strip().upper():
        return {"status": "REJECTED", "code": "SYMBOL_MISMATCH", "message": "manifest symbol does not match expected_symbol"}
    rows, fields = _parse_csv(bars_path)
    bars = _audit_bars(rows, fields)
    if bars["status"] == "REJECTED":
        return {"status": "REJECTED", "code": "BARS_CONTRACT_INVALID", "message": "bars.csv failed OHLCV audit", "manifest": manifest, "bars": bars}
    digest = hashlib.sha256(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"status": "READY", "code": "SNAPSHOT_AUDITED", "message": "snapshot integrity and OHLCV contract passed", "manifest": manifest, "bars": bars, "integrity": "MATCH", "dataset_id": f"sha256:{digest}"}


def audit_market_data(arguments: dict[str, Any]) -> dict[str, Any]:
    source_kind = arguments.get("source_kind")
    raw_path = arguments.get("path")
    expected_symbol = arguments.get("expected_symbol")
    if source_kind not in {"csv", "snapshot"}:
        return envelope("REJECTED", "INVALID_SOURCE_KIND", "source_kind must be csv or snapshot")
    if not isinstance(raw_path, str) or not os.path.isabs(raw_path):
        return envelope("REJECTED", "ABSOLUTE_PATH_REQUIRED", "path must be an absolute local path")
    path = Path(raw_path)
    try:
        if source_kind == "csv":
            if not path.is_file():
                return envelope("REJECTED", "CSV_MISSING", "CSV file does not exist")
            rows, fields = _parse_csv(path)
            report = _audit_bars(rows, fields)
            dataset_id = f"sha256:{_sha256(path)}"
            status = "OK" if report["status"] == "READY" else "REJECTED"
            return envelope(status, "CSV_AUDITED" if status == "OK" else "CSV_REJECTED", "CSV audit completed.", {"source_kind": "csv", "path": str(path), "dataset_id": dataset_id, "integrity": "MATCH", "quality": report}, warnings=["CSV 文件哈希只标识当前字节，不证明来源授权、复权经济含义或策略有效性。"], provenance={"data_source": "user-supplied-csv", "data_mode": "offline"})
        if not path.is_dir():
            return envelope("REJECTED", "PACKAGE_MISSING", "snapshot directory does not exist")
        report = _audit_snapshot(path, expected_symbol)
        status = "OK" if report.get("status") == "READY" else "REJECTED"
        return envelope(status, report.get("code", "SNAPSHOT_REJECTED"), report.get("message", "snapshot audit completed"), {"source_kind": "snapshot", "path": str(path), **report}, warnings=["完整性 MATCH 不证明授权、复权经济含义、数据正确性或策略有效性。"], provenance={"data_source": "auditable-market-snapshot", "data_mode": "offline"})
    except (OSError, UnicodeDecodeError, csv.Error, ValueError) as error:
        return envelope("REJECTED", "LOCAL_AUDIT_FAILED", str(error))


TOOL_DEFINITIONS = [
    {"name": "get_runtime_status", "description": "Check the local Chan Quant API without starting or stopping processes.", "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "resolve_instruments", "description": "Resolve an A-share name or code into backend-verified candidates.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8}}, "required": ["query"], "additionalProperties": False}},
    {"name": "inspect_instrument", "description": "Read a daily research dashboard and an independent current quote for one instrument.", "inputSchema": {"type": "object", "properties": {"symbol": {"type": "string"}, "as_of": {"type": "string", "format": "date"}}, "required": ["symbol"], "additionalProperties": False}},
    {"name": "compare_instruments", "description": "Compare 2 to 8 A-share instruments with no forward fill or FX conversion.", "inputSchema": {"type": "object", "properties": {"symbols": {"type": "array", "minItems": 2, "maxItems": 8, "items": {"type": "string"}}, "start": {"type": "string", "format": "date"}, "end": {"type": "string", "format": "date"}}, "required": ["symbols"], "additionalProperties": False}},
    {"name": "inspect_market_breadth", "description": "Read the observed Shanghai/Shenzhen A-share market breadth; refresh is remote and expensive.", "inputSchema": {"type": "object", "properties": {"refresh": {"type": "boolean", "default": False}}, "additionalProperties": False}},
    {"name": "audit_market_data", "description": "Audit a user-specified absolute CSV or immutable snapshot path without writing to it.", "inputSchema": {"type": "object", "properties": {"source_kind": {"type": "string", "enum": ["csv", "snapshot"]}, "path": {"type": "string"}, "expected_symbol": {"type": "string"}}, "required": ["source_kind", "path"], "additionalProperties": False}},
]

HANDLERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "get_runtime_status": get_runtime_status,
    "resolve_instruments": resolve_instruments,
    "inspect_instrument": inspect_instrument,
    "compare_instruments": compare_instruments,
    "inspect_market_breadth": inspect_market_breadth,
    "audit_market_data": audit_market_data,
}


def _rpc_result(request_id: Any, result: Any) -> dict[str, Any]:
    serialized = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": serialized}], "structuredContent": result}}


def _rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def dispatch(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")
    if method == "notifications/initialized" or method == "notifications/cancelled":
        return None
    if method == "initialize":
        return _rpc_result(request_id, {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "chan-quant", "version": PLUGIN_VERSION}})
    if method == "ping":
        return _rpc_result(request_id, {})
    if method == "tools/list":
        return _rpc_result(request_id, {"tools": TOOL_DEFINITIONS})
    if method == "tools/call":
        params = request.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        handler = HANDLERS.get(name)
        if handler is None:
            return _rpc_error(request_id, -32602, f"unknown tool: {name}")
        return _rpc_result(request_id, handler(arguments))
    if request_id is None:
        return None
    return _rpc_error(request_id, -32601, f"method not found: {method}")


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            response = dispatch(request)
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError as error:
            sys.stdout.write(json.dumps(_rpc_error(None, -32700, str(error))) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
