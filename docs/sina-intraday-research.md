# 新浪指数分时序列合同研究

## 结论

截至北京时间 **2026-08-01 22:34–22:37**，本次任务应判定为 **NO-GO**：不要继续实现“8 个指数的一分钟盘中分时曲线”。

新浪一手端点确实返回 8 个指数的分钟价格序列，但当前可见合同不能同时回答“这组分钟点属于哪一个交易日”和“交易时段内是否持续更新”。在周六的现场响应中，分钟线只有时刻，没有日期、时区或来源字段；把它标成 `Asia/Shanghai` 的 `2026-07-31` 只能依赖另一个 5 分钟端点做跨接口推断。该推断不满足交接文档要求的独立、可审计 `session_date` 合同，也没有交易时段内增量行为的实证。

`CN_MarketData.getKLineData?scale=5` 是一个有日期的 **5 分钟聚合序列候选**，8 个指数的最近完整交易时段均通过本次静态完整性检查。但它不是一分钟序列，而且本次恰逢周六，无法验证开市期间的部分会话、新鲜度或更新行为。若产品明确接受“五分钟盘中快照”，仍应先在下一个交易时段补做一次有界动态核验，再重新判定 GO。

## 已知仓库边界

- 首页 8 个稳定身份来自 [`frontend/src/marketInstruments.ts`](../frontend/src/marketInstruments.ts#L9-L18)，顺序与颜色来自 [`frontend/src/homeMarket.ts`](../frontend/src/homeMarket.ts#L27-L44)。
- 规范代码到新浪代码的既有映射为 `NNNNNN.SH/SZ -> sh/szNNNNNN`，见 [`backend/src/chan_quant/data/sina_source.py`](../backend/src/chan_quant/data/sina_source.py#L26-L31)。
- 当前 `MarketBar` 只有日期级 OHLCV，见 [`backend/src/chan_quant/domain/market.py`](../backend/src/chan_quant/domain/market.py#L8-L16)；`QuoteSnapshot` 是单个时间点，见 [`backend/src/chan_quant/domain/quote.py`](../backend/src/chan_quant/domain/quote.py#L9-L28)。仓库没有分钟序列模型、适配器或 API。
- 现有新浪 K 线实现固定 `scale=240`，见 [`backend/src/chan_quant/data/sina_source.py`](../backend/src/chan_quant/data/sina_source.py#L78-L113)；前端不得直连新浪，且分钟序列不能进入日 K/策略链路，沿用 [`docs/architecture.md`](architecture.md#L24-L60) 与 [`docs/data-contract.md`](data-contract.md#L114-L125) 的边界。
- 新浪地址是未文档化匿名端点，没有公开字段版本、SLA 或再分发授权；现有项目只允许本地、低频研究使用，见 [`docs/sina-data-source.md`](sina-data-source.md#L3-L7) 与 [`docs/sina-data-source.md`](sina-data-source.md#L69-L83)。

## 一手候选与现场行为

本次只使用仓库源码和新浪自有响应，没有使用个人媒体、第三方封装、Cookie、Token 或其他凭证。完整市场响应未写入 Git；临时 Python 探针只在内存中解析并输出汇总。

### 候选 A：K 线端点

一手地址：[`CN_MarketData.getKLineData`](https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData?symbol=sh000001&scale=5&ma=no&datalen=64)。仓库已有同一路径的日线适配器来源，见 [`backend/src/chan_quant/data/sina_source.py`](../backend/src/chan_quant/data/sina_source.py#L11-L14)。

| 粒度假设 | 现场结果 | 判断 |
|---|---|---|
| `scale=1` | HTTP `200`、`application/json; charset=gbk`、JSON `null` | 不支持本次一分钟合同 |
| `scale=5` | HTTP `200`；字段固定为 `day/open/high/low/close/volume`；`Cache-Control: max-age=10` | 可继续评估为 5 分钟聚合序列 |
| `scale=15/30/60` | 各返回相应时间间隔的 OHLCV 小样本 | 不属于本次一分钟目标 |
| 无效代码或 `scale=7` | HTTP `200` + JSON `null` | 必须归一化为“无数据/不支持”，不能当成功 |
| 缺少 `symbol` | HTTP `200` + `{"__ERROR":1,"__ERRORMSG":"Input error"}` | 必须解析应用层错误，不能只看 HTTP |

`scale=5&datalen=64` 对 8 个首页指数各请求一次。返回头的 `Date` 为 `Sat, 01 Aug 2026 14:34:33 GMT`，而每个响应的最近会话日期均为 `2026-07-31`，因此该端点在本次周六闭市观察中返回的是**最近可用交易时段**，不是当前自然日。

| 规范代码 | 新浪代码 | 最近会话点数 | 时段 | 重复 | 缺失/异常时刻 | 价格错误 |
|---|---|---:|---|---:|---|---:|
| `000001.SH` | `sh000001` | 48 | 09:35–11:30；13:05–15:00 | 0 | 0 | 0 |
| `399001.SZ` | `sz399001` | 48 | 09:35–11:30；13:05–15:00 | 0 | 0 | 0 |
| `399006.SZ` | `sz399006` | 48 | 09:35–11:30；13:05–15:00 | 0 | 0 | 0 |
| `000300.SH` | `sh000300` | 48 | 09:35–11:30；13:05–15:00 | 0 | 0 | 0 |
| `000905.SH` | `sh000905` | 48 | 09:35–11:30；13:05–15:00 | 0 | 0 | 0 |
| `000852.SH` | `sh000852` | 48 | 09:35–11:30；13:05–15:00 | 0 | 0 | 0 |
| `000688.SH` | `sh000688` | 48 | 09:35–11:30；13:05–15:00 | 0 | 0 | 0 |
| `000016.SH` | `sh000016` | 48 | 09:35–11:30；13:05–15:00 | 0 | 0 | 0 |

“价格错误”检查为：`open/high/low/close` 都是有限正数，且 `low <= open/close <= high`。8 条序列都严格单调、无重复，午间没有生成点，午间相邻时间差为 95 分钟。响应中的 `day` 是无时区字符串；将其解释为 `Asia/Shanghai` 符合当前沪深市场边界和时段形状，但**不是上游 payload 自带的时区声明**。payload 同样没有 `source` 或独立 `session_date` 字段，来源只能由后端适配器根据请求端点附加。

### 候选 B：一分钟分时端点

一手地址：[`CN_MinlineService.getMinlineData`](https://quotes.sina.cn/cn/api/openapi.php/CN_MinlineService.getMinlineData?symbol=sh000001)。

8 个代码都返回 HTTP `200`、`application/json; charset=utf-8`、`Cache-Control: max-age=30`，顶层形状为：

```json
{
  "result": {
    "status": {"code": 0, "msg": "MySql:lv1:success"},
    "data": [{"m": "09:30:00", "p": "..."}]
  }
}
```

上例只展示本次候选模型会考虑的 `m/p`；未提交完整响应。所有 8 个指数都包含 `m/p/avg_p/v/tot_v`，但只有 `sh000001` 额外出现 `hlz/lx`，证明不能把可选字段当成跨标的固定合同。本次只验证 `m` 为可解析时刻、`p` 为有限正数；`avg_p/v/tot_v/hlz/lx` 的精确定义没有一手文档，不应进入领域模型。

| 规范代码 | 点数 | 首末时刻 | 重复 | 明确缺失时刻 | `p` 错误 |
|---|---:|---|---:|---|---:|
| `000001.SH` | 240 | 09:30–15:00 | 0 | 13:00、14:59 | 0 |
| `399001.SZ` | 240 | 09:30–15:00 | 0 | 13:00、14:59 | 0 |
| `399006.SZ` | 240 | 09:30–15:00 | 0 | 13:00、14:59 | 0 |
| `000300.SH` | 239 | 09:30–15:00 | 0 | 13:00、14:58、14:59 | 0 |
| `000905.SH` | 239 | 09:30–15:00 | 0 | 13:00、14:58、14:59 | 0 |
| `000852.SH` | 240 | 09:30–15:00 | 0 | 13:00、14:59 | 0 |
| `000688.SH` | 239 | 09:30–15:00 | 0 | 13:00、14:58、14:59 | 0 |
| `000016.SH` | 240 | 09:30–15:00 | 0 | 13:00、14:59 | 0 |

所有序列严格单调、无重复，11:30 后的下一点为 13:01，午休中没有点。尾盘缺点在指数间不完全一致；即使未来采用该端点，也必须原样暴露缺口，不能插值、补零、前值填充或自行生成 13:00/14:58/14:59。

错误行为同样只在应用层表达：无效 `sh999999` 返回 `status.code=0` 和空数组；缺少 `symbol` 返回 `status.code=-1` 和空数组；传入规范代码 `000001.SH` 返回 `status.code=-1` 与 `data=null`。因此“HTTP 200 + code 0”仍不足以证明有可用序列。

### 日期绑定与闭市行为

一分钟 payload 的顶层、`result/status` 和每个数据点中都没有日期、时区或来源字段。对 `sh000001` 分别加入未经文档化的 `date=2026-07-30` 与 `day=2026-07-30`，响应与无日期参数响应的字节长度和 SHA-256 完全相同；这两个参数在本次观察中被忽略，不能建立历史或会话日期合同。该测试没有穷举所有可能参数，也没有找到新浪提供的开发者说明。

作为同源交叉检查，本次对每个指数再请求 `scale=5&datalen=1`：一分钟序列的 `15:00 p` 与 5 分钟序列的 `2026-07-31 15:00 close` 在 8 个指数上全部相等。这是“一分钟响应很可能对应最近完整的 `2026-07-31` 会话”的强现场证据，但仍是**跨端点推断**，不是一分钟响应自带的日期合同。交易时段内两个端点是否同时更新、是否指向同一会话、部分 5 分钟段与最新分钟点如何对应，本次没有条件验证。

## GO/NO-GO 分解

| 合同项 | `scale=5` | `getMinlineData` |
|---|---|---|
| 8 个代码映射 | 通过 | 通过 |
| 会话日期 | `day` 中可提取 `2026-07-31` | **缺失**；只能跨端点推断 |
| `Asia/Shanghai` | 时段吻合，但 payload 无时区 | 时段吻合，但 payload 无时区 |
| 单调/重复 | 通过 | 通过 |
| 午休 | 通过，无午休点 | 通过，无午休点 |
| 价格字段 | OHLC 现场可校验 | 只确认 `p` 为正数且终点与 5 分钟 close 相等 |
| 缺失点 | 最近完整会话未观察到缺点 | 固定和逐标的尾盘缺点并存 |
| 闭市/自然日 | 明确返回最近会话而非周六自然日 | payload 无法独立判断 |
| 错误响应 | HTTP 200 + `null`/`__ERROR` | HTTP 200 + `status`/空数组/`null` |
| 来源识别 | 只能由请求端点附加 | 只能由请求端点附加 |
| 交易时段增量与新鲜度 | **未验证** | **未验证** |
| 本次目标 | 不是一分钟粒度 | 核心日期与新鲜度合同不成立 |

因此，总体结论保持 **NO-GO**。缺失项不是绘图问题，而是后端无法在不猜测的情况下生成可靠的 `session_date/timezone/freshness`：

1. 不得把周六抓到的无日期分钟线标成“今日实时”；
2. 不得仅用 HTTP `Date` 当行情日期；
3. 不得用单点 Quote、日 K、插值或前值填充补出分钟历史；
4. 不得把这次闭市静态观察外推成开市时有稳定增量或正式 SLA。

解除 NO-GO 有两条可审计路径：

- 若接受 **5 分钟盘中快照**，在一个交易时段内低频复测 `scale=5` 的部分会话日期、末点推进、缓存/延迟和收盘转换；通过后把范围明确改为“五分钟”，不要称一分钟。
- 若必须是一分钟，采用能在同一响应中明确给出 `session_date`、时区、来源和新鲜度语义的正式数据源；或者在另行评审后接受 `getMinlineData + scale=5` 的双端点日期证明，并补齐交易时段内逐次一致性测试。后一方案仍保留匿名接口无 SLA、无授权说明和双上游耦合风险。

## 复现方式与边界

代表性最小探针：

```bash
cd backend
uv run python -c 'import httpx,json; u="https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"; r=httpx.get(u,params={"symbol":"sh000001","scale":"5","ma":"no","datalen":"64"},headers={"User-Agent":"ChanQuant/0.2 local-research"},timeout=10); p=json.loads(r.content.decode("gb18030")); print(r.status_code,r.headers.get("content-type"),r.headers.get("date"),len(p),p[0]["day"],p[-1]["day"],sorted(p[0]))'

uv run python -c 'import httpx; u="https://quotes.sina.cn/cn/api/openapi.php/CN_MinlineService.getMinlineData"; r=httpx.get(u,params={"symbol":"sh000001"},headers={"User-Agent":"ChanQuant/0.2 local-research","Referer":"https://finance.sina.com.cn/"},timeout=10); x=r.json()["result"]; d=x["data"]; print(r.status_code,r.headers.get("content-type"),r.headers.get("date"),x["status"],len(d),d[0]["m"],d[-1]["m"],sorted(d[0]))'
```

8 标的矩阵、错误控制和跨端点终点比对使用后端虚拟环境中的临时 Python 汇总脚本执行，请求次数保持为每个候选每标的一次量级。探针没有写入行情文件、Cookie、Token 或完整响应；本研究只证明上述时点的协议表现，不证明浏览器、生产行情、交易性能、商业授权或未来可用性。
