---
name: market-data-audit
description: Audit an explicitly supplied absolute CSV or immutable snapshot path and explain quality, integrity, and authorization boundaries.
---

# Market data audit

Use only when the user supplies an absolute local path and asks whether CSV or snapshot input meets the research contract. Call `audit_market_data` with `source_kind` and the path. The tool is read-only and must not expand the path, recurse into neighboring files, write data, or fall back to another provider.

For CSV, explain schema, valid rows, date range, OHLCV issues, history length, and the file hash. For snapshots, distinguish manifest/schema validation, bars hash integrity, dataset ID, adjustment declaration, and any external audit reference.

`integrity=MATCH` proves byte-level package consistency only. It does not prove provider authorization, adjustment economics, data correctness, or strategy effectiveness. Do not recommend using a rejected input by silently changing its mode.

