# 沪深 A 股日终市场温度数据包

## 用途与边界

数据包为 `CN_A_SH_SZ_V1` 提供一份可重算、可拒绝的日终原始输入。它不是聚合图表导出：必须保留逐证券 universe 与逐证券昨收/收盘输入。真实数据、Token、授权材料和缓存放在 Git 外；仓库中的测试行全部是合成 fixture，不代表真实市场。

```text
market-breadth-package/
├── manifest.json
├── universe.csv
└── quotes.csv
```

后端先检查 manifest、文件字节数和 SHA-256，再检查 CSV 表头、行数、身份、日期与重复记录。任何不一致返回 HTTP `422 REJECTED`，不会降级到匿名行情、演示值或旧快照。

## manifest.json

```json
{
  "schema_version": "market-breadth-package-v0.1",
  "market": "CN_A_SH_SZ_V1",
  "mode": "EOD",
  "timezone": "Asia/Shanghai",
  "session_date": "2026-07-31",
  "universe_id": "provider-or-exchange-snapshot-2026-07-31",
  "universe_as_of": "2026-07-31",
  "fetched_at": "2026-08-01T16:05:00+08:00",
  "source": "authorized-local-export",
  "universe_source": "official-exchange-or-authorized-master-data",
  "quote_source": "authorized-eod-provider",
  "license_note": "Describe the user-authorized local research boundary",
  "inclusion_rules": ["listed Shanghai and Shenzhen A-share stocks"],
  "exclusion_rules": ["BSE, B shares, funds, bonds and indices"],
  "universe_row_count": 5203,
  "quotes_row_count": 5203,
  "universe_bytes": 123456,
  "quotes_bytes": 234567,
  "universe_sha256": "<64 lowercase hex characters>",
  "quotes_sha256": "<64 lowercase hex characters>",
  "quality_policy_version": "market-breadth-quality-v0.1",
  "calculation_policy_version": "market-breadth-calculation-v0.1"
}
```

示例中的数量和字节数只是格式示意，不是可复用的市场事实。`universe_as_of` 必须等于 `session_date`；`fetched_at` 必须带 UTC offset。文件可以来自交易所官方名录加获授权日终行情，也可以来自一个能同时提供合法主数据和行情的正式导出，但来源、使用边界和哈希必须保留。

## universe.csv

固定表头：

```csv
symbol,exchange,security_name,security_type,board,list_date,delist_date
```

- `symbol` 必须是 `NNNNNN.SH` 或 `NNNNNN.SZ`，后缀与 `exchange` 一致；
- `security_type` 固定为 `A_STOCK`；
- `board` 只能是 `MAIN`、`STAR` 或 `CHINEXT`；
- `list_date <= session_date`；
- `delist_date` 可空，但若存在必须晚于 `session_date`；
- universe 中每个规范代码只能出现一次。

风险警示不会改变 A 股身份，因此不得仅因 `ST/*ST` 名称排除。停牌成员仍在 universe 中，其当日分类由 quotes 合同决定。

## quotes.csv

固定表头：

```csv
symbol,session_date,previous_close,last_price,unavailable_reason,provider_change_percent
```

- 可分类记录必须提供有限的 `previous_close` 和 `last_price`；后端使用 `(last_price - previous_close) / previous_close` 复算；
- `provider_change_percent` 使用百分数单位，例如 `1.25` 表示 `1.25%`，只用于交叉检查；
- 明确不可用的记录让价格列留空，并填写 `SUSPENDED`、`NO_TRADE_YET`、`MISSING_QUOTE`、`INVALID_PRICE` 或 `NO_REFERENCE_PRICE`；
- 没有 quotes 行的 universe 成员计为未知 `MISSING_QUOTE`，不属于 `explicitly_unavailable`；
- quote 中不允许出现 universe 以外的代码、重复代码或不同交易日。

## 12 个非零分桶

零涨跌单列为 `unchanged`。其余有效记录按以下数学边界唯一分类：

| ID | 边界 |
|---|---|
| `lt_m7` | `x < -0.07` |
| `m7_m5` | `-0.07 <= x < -0.05` |
| `m5_m3` | `-0.05 <= x < -0.03` |
| `m3_m2` | `-0.03 <= x < -0.02` |
| `m2_m1` | `-0.02 <= x < -0.01` |
| `m1_0` | `-0.01 <= x < 0` |
| `p0_p1` | `0 < x <= 0.01` |
| `p1_p2` | `0.01 < x <= 0.02` |
| `p2_p3` | `0.02 < x <= 0.03` |
| `p3_p5` | `0.03 < x <= 0.05` |
| `p5_p7` | `0.05 < x <= 0.07` |
| `gt_p7` | `x > 0.07` |

`market-breadth-quality-v0.1` 的可解释比例门槛为 `0.995`。`FAILED` 响应仍保留审计计数和问题原因，但前端不渲染柱状分布。

## 启动与接口

```bash
cd backend
CHAN_QUANT_MARKET_BREADTH_PACKAGE_PATH=/absolute/path/to/market-breadth-package \
uv run uvicorn chan_quant.api.app:app --host 127.0.0.1 --port 8000
```

```http
GET /api/v1/market-breadth?market=CN_A_SH_SZ_V1
```

自动下载 Tushare 日终数据、Tushare 盘中 `rt_k`、北交所 `.BJ` 和匿名网页全市场扫描都不属于当前运行时合同。
