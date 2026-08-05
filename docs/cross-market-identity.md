# 跨市场规范身份与比较语义

> 状态：`MARKET-001` 分支合同，2026-08-06
> 范围：身份与比较口径，不包含港股、美股或全球指数日 K/Quote Adapter

## 目标与非目标

本合同把“能识别一个标的”与“已获准读取它的行情”分开。后端 `InstrumentIdentity` 集中拥有规范代码、市场、交易所、ISO 10383 MIC、资产类别、ISO 4217 币种、IANA 时区、交易日历和 provider symbol。前端只展示这些字段，不从代码后缀猜测交易所、币种或行情能力。

本阶段不引入公共 CORS 代理、匿名跨市场行情端点、浏览器直连、汇率换算、盘前盘后行情或交易所假日日历计算。身份目录中的 `daily_bars=BLOCKED` 和 `quote=BLOCKED` 是产品事实，不是待前端隐藏的技术错误。

## 规范代码

| 市场 | 格式 | 示例 | 说明 |
|---|---|---|---|
| 沪深 | `NNNNNN.SZ` / `NNNNNN.SH` | `000001.SZ` | 保持现有合同；后缀可唯一确定交易所 |
| 港股 | `NNNNN.HK` | `00700.HK` | 固定五位，保留前导零 |
| 美股 | `TICKER.US` | `AAPL.US`、`BRK.B.US` | 后缀只表示美国市场，不能据此猜测 NASDAQ/NYSE/NYSE Arca |
| 全球指数 | `INDEX.GI` | `SPX.GI` | 只表示指数身份；具体发布或交易场所必须来自审计目录 |

规范化只做去除首尾空白和大写转换。除沪深外，代码格式本身不足以建立完整身份；未进入审计目录的代码返回 `IDENTITY_NOT_IN_AUDITED_CATALOG`，不能用占位名称或默认交易所补齐。

## 身份字段与不变量

`InstrumentIdentity` 新增以下市场上下文：

| 字段 | 语义 | 例子 |
|---|---|---|
| `market` | 产品级市场分类 | `CN`、`HK`、`US`、`GLOBAL` |
| `exchange` | 用户可读交易场所 | `HKEX`、`NASDAQ`、`CBOE` |
| `mic` | ISO 10383 市场标识 | `XHKG`、`XNAS`、`XCBO` |
| `currency` | ISO 4217 原始计价币种 | `HKD`、`USD` |
| `timezone` | IANA 时区 | `Asia/Hong_Kong`、`America/New_York` |
| `trading_calendar` | 交易日历身份 | 当前与 MIC 同名；不是内置假日计算器 |
| `provider_symbols` | 经来源确认的 provider 到代码映射 | `{"nasdaq": "AAPL"}` |

后端验证代码市场、交易所、MIC、币种、时区与日历必须一致。provider 名称统一为小写且键和值都不得为空。美股代码不能只凭 `.US` 推断交易所；全球指数必须使用 `asset_type=INDEX`。

## 当前审计目录

| 规范代码 | 身份 | 市场上下文 | 一手身份来源 | 行情能力 |
|---|---|---|---|---|
| `00700.HK` | 腾讯控股 | `HKEX / XHKG / HKD / Asia/Hong_Kong` | [HKEX Equities Quote](https://www.hkex.com.hk/Market-Data/Securities-Prices/Equities/Equities-Quote?sym=700&sc_lang=en) | 日 K、Quote 均 `BLOCKED` |
| `AAPL.US` | Apple Inc. | `NASDAQ / XNAS / USD / America/New_York` | [Nasdaq AAPL](https://www.nasdaq.com/market-activity/stocks/aapl) | 日 K、Quote 均 `BLOCKED` |
| `SPX.GI` | S&P 500 Index | `CBOE / XCBO / USD / America/New_York` | [Cboe SPX](https://www.cboe.com/tradable-products/sp-500/spx-options) | 日 K、Quote 均 `BLOCKED` |

目录的 `confirmed_at=2026-08-06` 只说明身份来源在该日核对。动态网页不是仓库内不可变证据，链接可访问也不证明行情字段合同、历史稳定性、SLA、许可或再分发权。时区名称遵循 [IANA Time Zone Database](https://www.iana.org/time-zones)；交易时段与节假日仍必须由未来获准 Adapter 的正式合同提供。

## 接口与失败关闭

```http
GET /api/v1/instruments/catalog
GET /api/v1/instruments/catalog?market=US
GET /api/v1/instruments/AAPL.US
```

目录和已审计身份是本地静态事实，不需要开启远端网络。以下请求在没有获准 Adapter 时固定返回 HTTP `422`：

```json
{
  "detail": {
    "status": "REJECTED",
    "code": "MARKET_DATA_ADAPTER_UNAVAILABLE",
    "message": "daily comparison has no authorized provider adapter for AAPL.US"
  }
}
```

失败关闭适用于 Dashboard 日 K、单标的 Quote、批量 Quote 和多标的远端比较。它不得回退到新浪沪深 Adapter、合成数据、旧缓存或前端代理。

## 跨市场比较口径

比较计算模块已经能消费不同市场的、由调用方明确提供的 `ComparisonInput`，但运行时路由仍只允许现有沪深新浪候选来源。输出固定携带：

- `date_basis=LOCAL_TRADING_DATE`：每根日 K 使用该标的 IANA 时区下的本地交易日；
- `session_scope=REGULAR_SESSION_CLOSE`：只比较常规交易时段收盘，不纳入盘前盘后；
- `timezone_mode=PER_INSTRUMENT_IANA`：同一 ISO 日期不等于同一绝对时刻；
- `currency_mode=NATIVE_NO_FX_CONVERSION`：收益各自在原币种内归一化，不做外汇换算；
- `overlap_policy=INTERSECTION_OF_COVERAGE_WINDOWS`：先取成功序列共同覆盖窗口；
- `missing_date_policy=NULL_NO_FORWARD_FILL`：窗口内取本地交易日并集，缺失值为 `null`。

当成功序列跨币种或跨时区时，后端分别输出 `NATIVE_CURRENCY_NO_FX_CONVERSION` 和 `LOCAL_TRADING_DATE_ALIGNMENT` 警告。前端只展示后端口径与警告，不自行换算或重定义“同一天”。

## 后续解除条件

每个新增市场的数据能力仍须分别完成：具体提供方与书面授权、provider symbol 合同、日 K/Quote 字段、币种与复权、常规/盘前盘后边界、时区与交易日历、停牌与缺行语义、真实交易时段验证、缓存和展示条款。只有这些证据进入数据源注册表并通过测试，目录中的对应能力才能从 `BLOCKED` 改变状态。
