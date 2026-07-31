# Dashboard API 数据契约

## 快照接口

```http
GET /api/v1/instruments/{symbol}/dashboard?timeframe=1d&as_of=2026-07-30&lookback=2y
```

未配置外部数据时，接口使用确定性合成日 K，并返回：

```json
{
  "is_mock": true,
  "instrument": {
    "data_source": "deterministic-synthetic",
    "adjustment": "not-applicable"
  },
  "strategy": {
    "version": "independent-v0.1.0",
    "rule_status": "DRAFT"
  }
}
```

合成数据只用于验证计算、API 和页面链路。其信号和事件统计不是历史回测或实盘表现。

## 数据源选择

优先读取显式环境变量：

```text
CHAN_QUANT_DATA_SOURCE=synthetic|csv|sina
```

为兼容旧启动方式，未设置该变量但存在 `CHAN_QUANT_CSV_PATH` 时仍进入 CSV 模式；两者都没有时使用确定性合成数据。

## CSV 输入契约

通过环境变量 `CHAN_QUANT_CSV_PATH` 指定本地 CSV 后，接口对 URL 中的标的代码计算同一套 Independent v0.1 草案规则：

| 环境变量 | 必填 | 含义 |
|---|---|---|
| `CHAN_QUANT_CSV_PATH` | 是 | CSV 绝对路径或可解析路径 |
| `CHAN_QUANT_ADJUSTMENT` | 否 | 数据源声明的复权口径，默认 `unspecified` |
| `CHAN_QUANT_INSTRUMENT_NAME` | 否 | 页面名称，默认使用大写标的代码 |

CSV 列：

| 列名 | 必填 | 规则 |
|---|---|---|
| `trade_date` 或 `date` | 是 | `YYYY-MM-DD` 或 `YYYYMMDD` |
| `open/high/low/close` | 是 | 有限正数；最高最低必须包含开收盘 |
| `volume` | 是 | 非负整数；可接受数值字符串如 `1000.0` |
| `amount` | 否 | 有限非负数 |

读取后按日期升序规范化；重复日期、非法 OHLC、缺列、非 UTF-8 文件和少于 92 根历史都会返回 HTTP `422`。`as_of` 会在计算前截断数据，因此截断后也必须保留至少 92 根。

CSV 模式返回 `is_mock=false` 和 `data_source=csv`，只代表行情不再是内置合成数据；`strategy.rule_status` 仍为 `DRAFT`。

## 新浪 K 线输入契约

新浪模式使用后端适配器访问未文档化匿名 K 线端点，前端不得跨域直连：

| 配置 | 默认值 | 约束 |
|---|---|---|
| `CHAN_QUANT_DATA_SOURCE` | 无 | 新浪模式必须为 `sina` |
| `CHAN_QUANT_SINA_DATALEN` | `2000` | 整数，范围 `92..10000` |
| `CHAN_QUANT_INSTRUMENT_NAME` | URL 标的代码 | 仅用于展示名称 |

仅支持规范代码 `NNNNNN.SZ` 和 `NNNNNN.SH`。适配器固定请求日线 `scale=240`、关闭新浪均线 `ma=no`，以确保所有 EMA/SMA 仍由本项目后端计算。

新浪响应没有成交额和复权字段，因此强制返回：

```json
{
  "is_mock": false,
  "instrument": {
    "data_source": "sina-undocumented-kline",
    "adjustment": "unknown"
  },
  "strategy": {
    "rule_status": "DRAFT"
  }
}
```

HTTP 非 200、连接失败、超时、编码或 JSON 畸形映射为 HTTP `502`；无效标的、配置或历史不足映射为 HTTP `422`。详细现场证据和授权边界见 `sina-data-source.md`。

## 核心约束

- 后端拥有全部策略计算和状态判断。
- 前端只格式化后端值，不重新判断多空、共振或操作结论。
- 指标卡当前以已格式化字符串传输；领域计算中的比例使用十进制，例如 `-0.2085` 显示为 `-20.85%`。
- 所有日期使用 ISO 8601。
- `headline_total = buy_total + sell_total + excluded_total`。
- 每个周期满足 `successes <= eligible <= total_signals`。
- 每个信号满足 `structure_at <= confirmed_at <= executable_at`；没有下一根 K 线时 `executable_at=null`。
- 事件收益使用确认后的下一根可用 K 线开盘价，目标索引为执行索引加 `N - 1`。

## 版本字段

快照必须包含 `strategy.version`、`strategy.parameter_version` 与 `strategy.rule_status`。未来任何规则或参数变化都必须产生新版本，避免相同日期的历史结果被静默改写。
