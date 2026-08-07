from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from mcp_server.client import ChanQuantClient
from mcp_server.errors import ChanQuantError
from mcp_server.server import HANDLERS, dispatch


class PluginContractTests(unittest.TestCase):
    def test_mcp_exposes_exactly_six_tools(self) -> None:
        response = dispatch({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        tools = response["result"]["structuredContent"]["tools"]
        self.assertEqual(
            {tool["name"] for tool in tools},
            {
                "get_runtime_status",
                "resolve_instruments",
                "inspect_instrument",
                "compare_instruments",
                "inspect_market_breadth",
                "audit_market_data",
            },
        )
        self.assertEqual(len(HANDLERS), 6)

    def test_rejects_non_loopback_api(self) -> None:
        with self.assertRaises(ChanQuantError) as context:
            ChanQuantClient(api_base="https://example.com")
        self.assertEqual(context.exception.code, "LOCAL_ADDRESS_REQUIRED")

    def test_audit_csv_preserves_hash_and_insufficient_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bars.csv"
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=["date", "open", "high", "low", "close", "volume"])
                writer.writeheader()
                writer.writerow({"date": "2026-01-02", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 100})
            result = HANDLERS["audit_market_data"]({"source_kind": "csv", "path": str(path)})
            self.assertEqual(result["status"], "REJECTED")
            self.assertEqual(result["code"], "CSV_REJECTED")
            self.assertTrue(result["data"]["dataset_id"].startswith("sha256:"))

    def test_tool_call_returns_structured_envelope(self) -> None:
        response = dispatch({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "compare_instruments", "arguments": {"symbols": ["600519.SH"]}},
        })
        payload = response["result"]["structuredContent"]
        self.assertEqual(payload["status"], "REJECTED")
        self.assertEqual(payload["code"], "INVALID_SYMBOLS")
        json.dumps(payload, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
