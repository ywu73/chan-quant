# 可审计历史行情快照 v0.1

## 目标与边界

可审计快照用于把一次研究结论绑定到一份明确、不可静默改写的本地输入。它验证文件完整性、manifest 合同和日 K 结构，不下载行情、不管理凭证，也不证明提供方授权、复权经济含义或策略有效性。

行情目录必须位于 Git 仓库之外：

```text
/absolute/path/to/market-snapshot/
├── manifest.json
└── bars.csv
```

`bars.csv` 沿用 `docs/data-contract.md` 的 CSV 列合同，至少包含 92 根有效日 K。

## manifest.json

```json
{
  "schema_version": "market-snapshot-v0.1",
  "symbol": "600519.SH",
  "instrument_name": "贵州茅台",
  "asset_type": "UNKNOWN",
  "price_precision": 2,
  "timeframe": "1d",
  "provider": "user-authorized-export",
  "adjustment": "qfq",
  "adjustment_basis": "provider-declared",
  "timezone": "Asia/Shanghai",
  "fetched_at": "2026-08-01T00:30:00+08:00",
  "data_from": "2018-01-02",
  "data_to": "2026-07-31",
  "bar_count": 2000,
  "bars_sha256": "<lowercase SHA-256 of bars.csv>",
  "license_note": "User-authorized local research export",
  "audit_reference": null
}
```

约束：

- `symbol` 必须是 `NNNNNN.SZ` 或 `NNNNNN.SH`，并与 Dashboard URL 完全一致；
- `timeframe` 当前只能是 `1d`；
- `timezone` 当前只能是 `Asia/Shanghai`，`fetched_at` 必须显式使用 `+08:00`；
- `adjustment` 只能是 `qfq`、`hfq` 或 `unadjusted`；
- `provider-declared` 会产生 `ADJUSTMENT_PROVIDER_DECLARED` 警告；
- `externally-audited` 必须同时给出非空 `audit_reference`；状态可以进入 `READY`，但仍返回 `ADJUSTMENT_EXTERNAL_AUDIT_REFERENCE` 信息，明确程序只记录引用而不会自行验证外部材料；
- `bars_sha256` 必须是小写 64 位十六进制；
- `data_from`、`data_to` 和 `bar_count` 必须与 CSV 实际内容一致。

## 生成 SHA-256

macOS：

```bash
shasum -a 256 /absolute/path/to/market-snapshot/bars.csv
```

Linux：

```bash
sha256sum /absolute/path/to/market-snapshot/bars.csv
```

把输出的 64 位小写哈希填入 `bars_sha256`。之后任何字节变化，包括追加空行，都会触发 `HASH_MISMATCH`。

## 启动

```bash
cd backend
CHAN_QUANT_DATA_SOURCE=snapshot \
CHAN_QUANT_DATA_PACKAGE_PATH=/absolute/path/to/market-snapshot \
uv run uvicorn chan_quant.api.app:app --host 127.0.0.1 --port 8000
```

打开与 manifest 标的一致的 URL。例如 manifest 是 `600519.SH`：

```text
http://127.0.0.1:5173/?symbol=600519.SH
```

## 失败关闭错误代码

| 代码 | 含义 |
|---|---|
| `PACKAGE_MISSING` | 数据包目录不存在 |
| `MANIFEST_MISSING` | 缺少 `manifest.json` |
| `MANIFEST_ENCODING` | manifest 不是 UTF-8 |
| `MANIFEST_READ_FAILED` | manifest 因本地文件系统错误无法读取 |
| `MANIFEST_JSON_INVALID` | manifest 不是有效 JSON |
| `MANIFEST_CONTRACT_INVALID` | 字段、枚举、时间或跨字段约束失败 |
| `BARS_MISSING` | 缺少 `bars.csv` |
| `BARS_READ_FAILED` | CSV 因本地文件系统错误无法读取 |
| `HASH_MISMATCH` | CSV 实际 SHA-256 与 manifest 不一致 |
| `BARS_CONTRACT_INVALID` | CSV 的 OHLCV、日期、重复或历史长度合同失败 |
| `SYMBOL_MISMATCH` | manifest 标的与 Dashboard URL 不一致 |
| `BAR_COUNT_MISMATCH` | manifest 根数与 CSV 不一致 |
| `DATE_RANGE_MISMATCH` | manifest 起止日期与 CSV 不一致 |

所有错误都返回 HTTP `422`，且不会自动切换到新浪、普通 CSV 或合成数据。

## 数据集身份与 as_of

`dataset_id` 是规范化 manifest 的 SHA-256。它标识完整输入数据包，而 `as_of` 只是本次策略计算的可见截止日期。因此：

- 同一数据包使用不同 `as_of` 时，`dataset_id` 不变；
- 修改 manifest 的数据来源、复权依据、范围或哈希时，`dataset_id` 改变；
- 修改 `bars.csv` 但不更新 manifest 时，请求因 `HASH_MISMATCH` 失败；
- 更新 CSV 和 manifest 后形成新的可审计数据集身份。
