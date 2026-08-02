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
CHAN_QUANT_DATA_SOURCE=synthetic|csv|sina|snapshot
```

为兼容旧启动方式，未设置该变量但存在 `CHAN_QUANT_CSV_PATH` 时仍进入 CSV 模式；两者都没有时使用确定性合成数据。

未设置该变量但存在 `CHAN_QUANT_DATA_PACKAGE_PATH` 时优先进入 snapshot 模式。snapshot 模式不会在数据包失败时降级到其他来源。

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

## 可审计历史快照契约

snapshot 模式要求 `CHAN_QUANT_DATA_PACKAGE_PATH` 指向仓库外目录，且目录中固定存在 `manifest.json` 和 `bars.csv`。后端先验证 manifest 合同与 `bars.csv` SHA-256，再复用 CSV 的 OHLCV 和时间序列校验；标的、周期、日期范围、根数或哈希不一致均返回 `422`。

有效快照在 Dashboard 顶层增加：

```json
{
  "data_quality": {
    "status": "WARNING",
    "integrity": "MATCH",
    "dataset_id": "sha256:<64 hex chars>",
    "schema_version": "market-snapshot-v0.1",
    "provider": "authorized-local-export",
    "adjustment": "qfq",
    "adjustment_basis": "provider-declared",
    "timeframe": "1d",
    "timezone": "Asia/Shanghai",
    "fetched_at": "2026-08-01T00:30:00+08:00",
    "data_from": "2018-01-02",
    "data_to": "2026-07-31",
    "bar_count": 2000,
    "bars_sha256": "<64 hex chars>",
    "license_note": "User-authorized local research export",
    "audit_reference": null,
    "issues": [
      {
        "code": "ADJUSTMENT_PROVIDER_DECLARED",
        "severity": "WARNING",
        "message": "复权口径来自数据提供方声明……"
      }
    ]
  }
}
```

`dataset_id` 由规范化 manifest 生成。同一数据包在不同请求和不同 `as_of` 计算视图中保持相同；manifest 发生语义变化则身份变化。`integrity=MATCH` 只表示文件哈希与结构合同一致，不表示外部授权、复权经济含义、策略收益或实盘能力已验证。完整 manifest 见 `market-snapshot.md`。

非 snapshot 数据模式返回 `data_quality=null`，不会为缺少 manifest 和不可变文件身份的输入伪造数据集审计结论。

快照校验失败返回 HTTP `422` 和结构化拒绝原因，前端不得生成策略页面：

```json
{
  "detail": {
    "status": "REJECTED",
    "code": "HASH_MISMATCH",
    "message": "bars.csv SHA-256 ... does not match manifest ..."
  }
}
```

## 沪深 A 股日终市场温度契约

```http
GET /api/v1/market-breadth?market=CN_A_SH_SZ_V1
```

该接口与 Dashboard 的 `CHAN_QUANT_DATA_SOURCE` 独立，只读取 `CHAN_QUANT_MARKET_BREADTH_PACKAGE_PATH` 指向的 Git 外审计包。首版固定为 `mode=EOD`，universe 只含上交所主板、科创板、深交所主板和创业板的在市 A 股股票；不含北交所、B 股、基金、债券或指数。

`market-breadth-package-v0.2` 允许在相同领域合同下附带逐批原始 evidence、抓取窗口与提供方逐行日期证据。使用 `sina-hq-undocumented-observed-v0.1` 时，后端必须输出 `SINA_UNDOCUMENTED_SOURCE` 风险；证据哈希只证明本地字节完整，不升级为新浪字段承诺、SLA 或授权。页面请求不得触发新浪全市场扫描。

后端使用每条行情的当日 `previous_close` 与 `last_price` 通过 Decimal 复算涨跌。精确零差额只计入 `unchanged`，不进入 12 个柱状分桶；停牌、无交易、无合法参考价和缺失行情进入 `unavailable`，不得默认为平盘。

```text
sum(bin.count) = advancers + decliners
advancers + decliners + unchanged = covered
covered + unavailable = universe_total
coverage_ratio = covered / universe_total
resolution_ratio = (covered + explicitly_unavailable) / universe_total
```

`COMPLETE` 表示所有成员都已分类或有可验证的不可用原因；`PARTIAL` 表示存在未知缺行但 `resolution_ratio >= 0.995`；`FAILED` 表示低于版本化门槛或没有有效覆盖，前端不得展示分布。manifest、哈希、身份、日期、重复行或负价格不成立时返回 HTTP `422` 和结构化 `REJECTED`，不会回退到新浪、上一次快照或演示数字。

完整 manifest、CSV 字段和 12 桶边界见 `market-breadth-package.md`；数据源 GO/NO-GO 证据见 `a-share-market-breadth-research.md`。

## 新浪 K 线输入契约

新浪模式使用后端适配器访问未文档化匿名 K 线端点，前端不得跨域直连：

| 配置 | 默认值 | 约束 |
|---|---|---|
| `CHAN_QUANT_DATA_SOURCE` | 无 | 新浪模式必须为 `sina` |
| `CHAN_QUANT_SINA_DATALEN` | `2000` | 整数，范围 `92..10000` |

新浪模式下的标的身份通过同一后端元数据适配器解析，包括名称、交易所、可确认的资产类别和价格精度；解析失败时显示规范代码、使用两位价格和未知类别。`CHAN_QUANT_INSTRUMENT_NAME` 只用于外部 CSV 模式，不能覆盖新浪 URL 标的的名称。

仅支持规范代码 `NNNNNN.SZ` 和 `NNNNNN.SH`。适配器固定请求日线 `scale=240`、关闭新浪均线 `ma=no`，以确保所有 EMA/SMA 仍由本项目后端计算。

新浪响应没有成交额或复权声明。2026-07-31 的三只股票除权窗口核验均与原始未复权 OHLC 一致，因此类型 `11` 的当前股票/指数候选沿用一个**证据有界的观测标签**：

```json
{
  "is_mock": false,
  "instrument": {
    "data_source": "sina-undocumented-kline",
    "adjustment": "unadjusted-observed",
    "asset_type": "UNKNOWN",
    "price_precision": 2
  },
  "strategy": {
    "rule_status": "DRAFT"
  }
}
```

该值不是 `unadjusted`、`qfq` 或 `hfq` 的上游合同。它只表示当前审计证据支持“现场表现为不复权”；新浪没有公开字段合同、口径版本或 SLA，未来响应仍可能变化。前端必须同时展示这一限制，策略结论不得省略该警告。

现场类别 `203` 的 ETF 返回：

```json
{
  "instrument": {
    "symbol": "513100.SH",
    "name": "纳指ETF国泰",
    "exchange": "SH",
    "asset_type": "ETF",
    "price_precision": 3,
    "adjustment": "unspecified"
  }
}
```

`unspecified` 表示 ETF 行情可读取，但该 ETF 的复权、分红和份额折算口径尚未审计。三只股票样本的证据不得外推到 ETF。元数据不可用时也返回 `adjustment=unspecified`，避免把未知标的误写成已经观察到不复权。

HTTP 非 200、连接失败、超时、编码或 JSON 畸形映射为 HTTP `502`；无效标的、配置或历史不足映射为 HTTP `422`。详细现场证据和授权边界见 `sina-data-source.md`。

## 核心约束

- 后端拥有全部策略计算和状态判断。
- 前端只格式化后端值，不重新判断多空、共振或操作结论。
- 指标卡当前以已格式化字符串传输；股票/未知类别默认使用两位价格，ETF 使用三位价格。领域计算中的比例使用十进制，例如 `-0.2085` 显示为 `-20.85%`。
- 所有日期使用 ISO 8601。
- `headline_total = buy_total + sell_total + excluded_total`。
- 每个周期满足 `successes <= eligible <= total_signals`。
- 每个信号满足 `structure_at <= confirmed_at <= executable_at`；没有下一根 K 线时 `executable_at=null`。
- 事件收益使用确认后的下一根可用 K 线开盘价，目标索引为执行索引加 `N - 1`。

## 多标的走势对比接口

```http
GET /api/v1/market-comparison?symbols=000001.SZ&symbols=600000.SH&start=2025-01-01&end=2026-07-31
```

`symbols` 必须包含 2–8 个不同的规范沪深代码。`start` 和 `end` 可选，均为 ISO 8601 日期，且开始日期不得晚于结束日期。v0.1 比较端点只支持 `CHAN_QUANT_DATA_SOURCE=sina`；单个 CSV 或单个快照数据包不能表达多个标的，因此会明确返回 `422`，不会把同一份文件重复标记为多个证券。板块 preset 和自定义板块属于前端组合入口，不改变此后端校验合同；后端不会信任前端已经执行数量检查或去重。

响应以成功序列的共同覆盖窗口为范围，以该窗口内实际出现的交易日并集作为统一日期轴。每条序列的 `values` 与 `dates` 等长，值为相对该序列首个有效收盘价的十进制收益；缺失日为 `null`，不做前向填充：

```json
{
  "status": "PARTIAL",
  "requested": ["000001.SZ", "300001.SZ", "600000.SH"],
  "succeeded": 2,
  "failed": 1,
  "requested_from": "2025-01-01",
  "requested_to": "2026-07-31",
  "common_from": "2025-01-02",
  "common_to": "2026-07-31",
  "dates": ["2025-01-02", "2025-01-03"],
  "series": [
    {
      "instrument": {"symbol": "000001.SZ", "name": "示例", "exchange": "SZ", "asset_type": "UNKNOWN", "price_precision": 2},
      "data_source": "sina-undocumented-kline",
      "adjustment": "unadjusted-observed",
      "currency": "CNY",
      "is_mock": false,
      "data_from": "2025-01-02",
      "data_to": "2026-07-31",
      "baseline_at": "2025-01-02",
      "baseline_price": 10.25,
      "latest_close": 11.48,
      "previous_trading_day_return": -0.0061,
      "values": [0.0, null],
      "cumulative_return": 0.12,
      "max_drawdown": -0.18,
      "max_drawdown_peak_at": "2025-09-10",
      "max_drawdown_trough_at": "2025-11-03",
      "coverage_ratio": 0.99,
      "warnings": [{"code": "DATA_SOURCE_ADJUSTMENT_UNCONTRACTED", "message": "示例风险说明"}]
    }
  ],
  "failures": [{"symbol": "300001.SZ", "code": "UPSTREAM_UNAVAILABLE", "message": "示例上游故障"}]
}
```

上述数字和名称只是合同示例，不是真实市场结果。`COMPLETE` 表示所有请求标的成功，`PARTIAL` 表示至少一个成功且至少一个失败，`FAILED` 表示没有可输出的曲线。批量接口以 `200` 返回逐项失败，只有请求合同或全局数据模式不成立时返回 `422`。

`baseline_price` 是共同覆盖窗口内该标的首个有效收盘价，`latest_close` 是请求日期范围内最后一个有效收盘价；两者都属于历史日 K，不是当前实时价格。`previous_trading_day_return` 使用窗口内倒数第二个有效交易日收盘价相对倒数第三个有效交易日收盘价计算，少于三个有效交易日时为 `null`。这些值和累计收益、最大回撤一样由后端计算，前端只按标的精度格式化。

`max_drawdown` 使用有效收盘价序列的历史峰值到后续谷值计算，返回非正十进制值，并同时给出峰值日与谷值日。未出现收盘价回撤时为 `0`，两个日期为 `null`。这不是组合资金曲线，也不包含交易成本、分红复权修复、汇率转换或可执行交易假设。

## 证券搜索接口

```http
GET /api/v1/instruments/search?q=纳指ETF%20国泰%20513100&limit=8
```

该接口由后端访问新浪未文档化标的建议端点，前端不得直连。当前只保留现场类型 `11` 和 ETF 类型 `203`，且代码必须可规范化为 `NNNNNN.SZ` 或 `NNNNNN.SH`。类型 `11` 可能包含股票与指数别名，因此返回 `asset_type=UNKNOWN`；类型 `203` 返回 `asset_type=ETF`：

```json
{
  "query": "纳指ETF 国泰 513100",
  "items": [
    {
      "symbol": "513100.SH",
      "name": "纳指ETF国泰",
      "exchange": "SH",
      "asset_type": "ETF",
      "price_precision": 3
    }
  ],
  "source": "sina-undocumented-suggest",
  "limit": 8
}
```

`q` 去除首尾空白后长度必须为 `1..40`，`limit` 必须为 `1..20`。无匹配返回空数组；输入错误返回 `422`，连接、HTTP、编码、赋值语句或字段合同异常返回 `502`。六位代码可能同时对应不同市场，前端必须展示候选结果，不能静默猜测交易所；URL 中的完整规范代码可以直接进入 Dashboard。

```http
GET /api/v1/instruments/513100.SH
```

单标的身份接口使用同一后端适配器精确解析规范代码并返回完整 `InstrumentIdentity`。比较页直接输入代码时，必须先取得该身份，才能把它加入可持久化的自定义板块；解析失败时不得保存占位名称、猜测资产类型或默认价格精度。

搜索结果是未文档化候选元数据，只用于选择单标的研究页面，不是正式证券主数据、全市场行情扫描或策略筛选结果。`203 -> ETF` 是 2026-07-31 对 `510300`、`159915`、`588000` 和 `513100` 等样本的现场观察，不是新浪公开合同。

## 独立实时 Quote 接口

```http
GET /api/v1/instruments/{symbol}/quote
```

该接口始终访问后端新浪实时快照适配器，不受 `CHAN_QUANT_DATA_SOURCE` 影响，也不会调用 Dashboard 构建器。只支持 `NNNNNN.SZ` 和 `NNNNNN.SH`：

```json
{
  "symbol": "000001.SZ",
  "name": "测试名称",
  "last_price": 11.62,
  "previous_close": 11.48,
  "change": 0.14,
  "change_percent": 0.012195,
  "open": 11.48,
  "high": 11.67,
  "low": 11.42,
  "volume": 63210000,
  "quote_at": "2026-07-31T14:35:06+08:00",
  "received_at": "2026-07-31T14:35:07+08:00",
  "source": "sina-undocumented-quote",
  "status": "LIVE",
  "is_stale": false
}
```

示例数值是合同样例，不是真实行情快照。`change = last_price - previous_close`，`change_percent = last_price / previous_close - 1`；计算由后端完成，前端只格式化。

时间与状态合同：

| 字段/状态 | 含义 |
|---|---|
| `quote_at` | 新浪响应内的行情日期与时间，固定解释为上海时区 |
| `received_at` | 后端收到本次响应的时间，不得冒充行情时间 |
| `LIVE` | 同一日期、15:00 前且行情时间距离接收时间不超过 30 秒 |
| `DELAYED` | 尚未满足收盘条件但与接收时间相差超过 30 秒；`is_stale=true` |
| `CLOSED` | 行情日期早于接收日期，或行情时间达到 15:00；`is_stale=false` |

`CLOSED` 只描述该快照已处于收盘口径，不证明交易所日历、停牌状态或端点完整性。响应行情时间比接收时间超前超过 5 秒会视为畸形上游响应。

错误映射：

| HTTP | 分类 | 例子 |
|---|---|---|
| `422` | 输入合同错误 | 非规范 symbol |
| `502` | 上游请求或响应故障 | 403、超时、解码失败、变量名或字段畸形 |
| `503` | 当前快照不可用 | 空字符串、全零快照，或开高低与成交量均为零的非交易快照 |

前端失败时不得无标记地延续旧价；Quote 故障不得阻断 Dashboard 或改变任何 `structure_at/confirmed_at/executable_at`。

比较页只对历史比较成功的标的启动独立 Quote 轮询。每个标的的成功、失败和 stale 状态单独展示；一个 Quote 失败不得清空其他标的，也不得清空历史曲线和历史指标。切换组合、重新生成结果、页面隐藏或组件卸载时必须中止旧请求并抑制晚到响应。`last_price` 和 `change_percent` 始终标为独立行情快照，不能覆盖 `baseline_price`、`latest_close`、`previous_trading_day_return` 或其他历史比较结论。

## 版本字段

快照必须包含 `strategy.version`、`strategy.parameter_version` 与 `strategy.rule_status`。未来任何规则或参数变化都必须产生新版本，避免相同日期的历史结果被静默改写。
