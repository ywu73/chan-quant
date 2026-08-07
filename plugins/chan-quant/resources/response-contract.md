# Response contract

Every Tool returns an envelope:

```json
{
  "status": "OK | PARTIAL | REJECTED | UNAVAILABLE",
  "code": "STABLE_REASON_CODE",
  "message": "human-readable summary",
  "data": {},
  "warnings": [],
  "provenance": {
    "plugin_version": "0.2.0",
    "data_source": "...",
    "data_mode": "...",
    "strategy_version": "independent-v0.1.0-draft",
    "parameter_version": "..."
  }
}
```

The backend's `422`, `502`, and `503` distinctions are preserved as stable reason codes. A missing service is `LOCAL_SERVICE_UNAVAILABLE`; remote-disabled input is `REMOTE_NETWORK_DISABLED`; malformed or non-Chan Quant responses fail closed. The plugin never substitutes synthetic data, stale cache, screenshots, or another provider after failure.

Daily model timestamps and independent Quote timestamps must remain separate. Structural and signal results must preserve `structure_at`, `confirmed_at`, and `executable_at`.
