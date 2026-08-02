# A 股市场温度数据合同研究

## 2026-08-02 产品决策更新

本文件下方保留的是实现前数据源研究结论。随后产品明确选择“无需本地包、运行时直接读取远端”的便利性优先方案，并接受匿名新浪端点没有公开字段合同、SLA、授权保证和持久审计证据的限制。

实现边界因此调整为：上交所官方 JSON 与深交所官方 XLSX 只用于建立当前沪深 A 股分母，新浪 `hq.sinajs.cn` 逐证券响应提供带日期的昨收与最新价；结果固定标记为 `mode=OBSERVED`，并同时输出 `REMOTE_OBSERVATION_NOT_AUDITABLE` 和 `SINA_UNDOCUMENTED_SOURCE`。普通请求只使用 300 秒进程内缓存，显式刷新重新获取，失败不回退到旧值。该方案是研究观察，不是可审计快照、正式行情服务或实盘交易依据。

这项产品决策扩大了原研究的 NO-GO 边界，但没有推翻下方关于匿名接口稳定性、许可和时点风险的事实判断。

## 原始研究结论

截至 **2026-08-02 14:53（Asia/Shanghai，星期日）**，截图所示的 A 股市场温度可以实现，但当前证据只支持以下分层结论：

| 形态 | 当前结论 | 可接受的实现边界 |
|---|---|---|
| 可审计日终快照 | **GO（有条件）** | 使用正式、有权限的数据导出，或用户提供的合法原始文件，在 Git 外保存逐证券 universe 与日线输入；后端复算涨跌方向、12 个分桶、覆盖率和质量状态 |
| 自动拉取日终数据 | **NO-GO（当前配置）** | Tushare `daily` 的公开文档支持按交易日一次取得最多 6000 条，但实际调用需要 Token；本次没有使用用户凭证，也没有验证当前账号权限、许可或完整真实响应 |
| 正式盘中批量版 | **NO-GO（当前证据）** | Tushare `rt_k` 的第一方文档表明可一次提取最多 6000 条全市场实时日 K，但它需要单独权限；还缺真实交易时段响应、`trade_time` 格式、全量覆盖、停牌语义、批次时点偏差和调用频率核验 |
| 新浪/东方财富匿名网页接口盘中版 | **NO-GO** | 现场可返回批量行情，但没有找到公开字段合同、版本、SLA 或再分发授权；新浪响应还缺交易日期，不能成为默认运行时依赖 |

因此，首版应是 **`CN_A_SH_SZ_V1` 的可审计日终市场温度**，而不是把匿名网页响应直接接到首页。盘中版只能在用户明确提供并授权使用正式批量行情权限后，经过真实交易时段动态核验再转为 GO。

这是一项产品范围扩展：当前 [`docs/product-spec.md`](product-spec.md) 仍把“全市场扫描与市场温度”列为 v0.1 非目标。研究结论不等于业务代码已经获得实现合同。

## 研究问题与事实边界

本研究只回答：

1. 哪些证券属于首版 A 股市场温度的分母；
2. 哪类数据源能在一个可解释时点提供昨收、最新价或收盘价；
3. 如何把缺失、停牌、上市首日与不一致数据显式留在质量合同中；
4. 后端应在哪个 seam 隔离正式运行时数据源和离线审计包。

本研究不证明：

- 匿名网页接口具有稳定性、许可或实时行情 SLA；
- 本地响应等同于交易所生产行情；
- 任何图表、回测或市场温度可以用于实盘交易；
- 截图中的 `5533`、`4690`、`728`、`115` 是可复用的固定值。

## `CN_A` universe 候选

### 首版：`CN_A_SH_SZ_V1`

首版只纳入 **上海证券交易所和深圳证券交易所官方 A 股列表中的已上市证券**。2026-08-02 现场可复现的构建来源是：

- 上交所[股票列表页面](https://www.sse.com.cn/assortment/stock/list/share/)及其[页面实际查询脚本](https://www.sse.com.cn/xhtml/home/2021public/querySearch/search_stocksDepositoryReceipts_2021.js)，调用上交所官方 [`commonQuery.do`](https://query.sse.com.cn/sseQuery/commonQuery.do)：`sqlId=COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L`、`STOCK_TYPE=1`（主板 A 股）或 `8`（科创板）、`COMPANY_STATUS=2,4,5,7,8`；
- 深交所[股票列表页面](https://www.szse.cn/market/product/stock/list/index.html)及官方 [A 股列表 JSON](https://www.szse.cn/api/report/ShowReport/data?SHOWTYPE=JSON&CATALOGID=1110&TABKEY=tab1&PAGENO=1) / [XLSX](https://www.szse.cn/api/report/ShowReport?SHOWTYPE=XLSX&CATALOGID=1110&TABKEY=tab1)。

现场计数是上交所主板 A 股 `1698`、科创板 `612`，深交所 A 股 `2893`，合计 `5203`。但上交所响应没有官方有效日期，深交所 `subname=2026-07-31`，所以 `5203` 只能写作不同版本证据的现场合计，不能冒充严格同一有效日的官方总数。

具体规则：

- 包含上海主板、科创板、深圳主板、创业板；
- 包含风险警示股票，因为风险警示不改变其“已上市 A 股股票”身份；
- 包含全天停牌成员，但它们进入 universe 后是否能分类由行情质量合同决定；
- `list_date <= session_date`，且在该交易日没有已经生效的终止上市状态；
- 上交所保存 `A_STOCK_CODE/SEC_NAME_CN/LIST_BOARD/LIST_DATE/DELIST_DATE` 及来源状态原值；深交所保存 `bk/agdm/agjc/agssrq`；证券身份不能只用代码前缀猜测；
- 上交所公开页面没有解释 `STATE_CODE/STATE_CODE_STOCK/PRODUCT_STATUS` 的业务枚举，深交所 A 股列表没有停牌字段，因此两者都不能被用来猜测当日停牌。

首版排除：

- 北交所股票（作为下一节独立 universe）；
- B 股、基金、ETF、LOF、REIT、债券、可转债、期权、存托凭证、其他非 A 股证券类别，以及交易所官方分类不明确的记录；
- 尚未上市、已终止上市、退市整理期结束或只存在于行情商预告列表的证券；
- 指数和板块代码。

版本化 universe 至少保存：`schema_version`、`universe_id`、`as_of`、`fetched_at`、`symbol`、`exchange`、`security_name`、`security_type`、`board`、`list_date`、`delist_date/list_status`、来源 URL/请求参数/文件名和 SHA-256。上交所没有 `as_of` 时必须写成 fetched-at snapshot，不能伪造官方有效日；深交所保留 `subname`。历史快照不能用“今天的在市列表”倒推过去的成员，否则会引入存活者偏差。

### 北交所：`CN_A_BJ_V1` 单列

北交所不应静默并入首版沪深分母。原因不是北交所不属于 A 股市场，而是当前 Chan Quant 的规范证券身份只覆盖 `.SH/.SZ`，而正式行情与主数据需要 `.BJ` 的独立身份、交易所和状态合同。北交所官方[上市公司列表页面](https://www.bse.cn/nq/listedcompany.html)实际使用 `POST https://www.bse.cn/nqxxController/nqxxCnzq.do` 的分页 JSONP；2026-08-02 现场为 `totalElements=331`、`totalPages=17`，样本 `920000` 安徽凤凰和 `920001` 纬达光电，样本业务日期字段 `xxjsrq=20260731`。

北交所版本应单独完成：

- 官方在市证券列表与历史状态快照；
- `.BJ` 代码规范化及测试；
- 与沪深相同的 `previous_close/last_price/trading_status` 合同；
- 首发日、停牌和无昨收的处理；
- UI 明确显示“沪深”或“沪深北”，不得仍写模糊的“A 股全市场”。

### universe 与行情必须独立版本化

行情商的“全市场”筛选不能代替 universe。2026-08-02 的有界现场请求已经显示，交易所官方列表现场合计为沪深 `5203`、北交所 `331`，但版本日期并不完全相同；不同匿名网页接口又分别给出新浪 `hs_a=5533` 和东方财富候选筛选 `total=5545`。匿名端点没有公开说明纳入未上市、北交所、特殊证券或状态异常记录的完整规则，因此只能作为反例：**批量行情返回了多少行，不等于产品分母应该是多少。**

## 数据源调查

### 正式、有凭证的数据源：Tushare Pro

Tushare 是候选数据提供方，以下事实只来自其第一方文档：

| 能力 | 第一方合同 | 对市场温度的意义 |
|---|---|---|
| 股票列表 `stock_basic` | 当前正常上市股票可以一次拉取；文档写明需要至少 2000 积分、每分钟 50 次 | 可作构建期主数据候选，但历史 `as_of` 仍需快照或历史列表 |
| 历史股票列表 `bak_basic` | 按 `trade_date` 提取历史每日股票列表，单次最多 7000 条，正式权限需 5000 积分 | 可作历史 universe 候选，仍需现场核验其证券类型和状态覆盖 |
| 日线 `daily` | 每交易日 15–16 点入库；按 `trade_date` 可取当日全部日线；每次最多 6000 条；停牌期间不提供数据 | 日终逐证券价格源候选；缺行不能自动解释为平盘 |
| 日线价格字段 | `close`、`pre_close`、`change`、`pct_chg`；文档明确 `pct_chg` 使用除权后的昨收 | 可避免直接拿前一交易日未调整收盘价跨除权计算 |
| 停复牌 `suspend_d` | 按交易日返回 `S/R` 与日内停牌区间；更新时间写作“不定期” | 可以解释部分缺行，但不能假定其与日线同时完成，必须保留未知原因 |
| 实时日 K `rt_k` | 支持代码通配符或多代码；单次最多 6000 条，文档称等同一次提取全市场；含 `pre_close/close/trade_time`；需单独开权限 | 最接近盘中市场温度的正式批量源候选 |
| 实时分钟 `rt_min` | 多代码、每次最多 1000 行，需正式权限 | 市场温度只需要当前快照，不应为 5000 多只股票抓分钟历史 |

第一方来源：

- [股票列表 `stock_basic`](https://tushare.pro/document/2?doc_id=25)
- [历史股票列表 `bak_basic`](https://tushare.pro/document/2?doc_id=262)
- [A 股日线 `daily`](https://tushare.pro/document/2?doc_id=27)
- [每日停复牌 `suspend_d`](https://tushare.pro/document/2?doc_id=214)
- [A 股实时日线 `rt_k`](https://tushare.pro/document/2?doc_id=372)
- [A 股实时分钟 `rt_min`](https://tushare.pro/document/2?doc_id=374)
- [交易日历 `trade_cal`](https://tushare.pro/document/2?doc_id=26)

2026-08-02 对 `https://api.tushare.pro` 发出的无 Token、无敏感信息日线请求返回 HTTP 业务错误 `code=40101`、`data=null`，响应 SHA-256 为 `fb791f8d8be3375e347ad867d39c46af62ea2906bea7dfbb25a48c806735cc8e`。这只证明当前调用需要凭证，不证明任一用户账号已经购买相关权限。

#### Tushare 日终版判定

**数据能力 GO，当前在线配置 NO-GO，外部审计包 GO。**

`daily(trade_date)` 的 6000 行上限能够容纳当前单日沪深 A 股数量，字段足以计算方向和分桶。但正式落地必须满足：

1. 用户明确授权使用自己的 Token 与对应数据权限；
2. Token 只进入环境变量或系统密钥存储，不进入 Git、日志或研究文档；
3. universe、`daily` 原始行和停复牌/缺失原因写入 Git 外快照包并带哈希；
4. 拉取时间不得早于提供方声明的完成窗口，且要用交易日历确认 `session_date`；
5. `daily` 缺行先记为 `unavailable: MISSING_DAILY_ROW`，只有额外证据才能细分为全天停牌；
6. 不把 Tushare 的接口权限等同于展示、缓存或再分发许可；使用前另行确认用户订阅条款。

#### Tushare 盘中版判定

**条件式 GO，当前 NO-GO。**

`rt_k` 的文档形状足够接近需求，但必须在一个真实交易日先完成有界动态核验：

- 明确 `trade_time` 是否包含交易日期、时区和秒级语义；
- 证明显式请求 `.SH/.SZ` universe 后没有混入基金、B 股、北交所或未上市证券；
- 证明 `pre_close`、`close` 与可选 `trade_time` 在开盘、午休、下午恢复、收盘后保持可解释；
- 区分尚未成交、全天停牌、临时停牌、上市首日和上游缺失；
- 若分批请求，记录 `snapshot_started_at`、`snapshot_completed_at`、最早/最晚 `trade_time` 并限制批次时间偏差；
- 核对当前订阅的每分钟限额、全市场请求许可、缓存和展示条款。

在这些门槛通过前，不实现正式盘中温度，不用 `rt_min` 对全市场逐证券抓取，也不把日终数据标成实时。

### 新浪匿名网页接口

2026-08-02（周日）的低频有界请求使用新浪自有域名：

- [`Market_Center.getHQNodeStockCount?node=hs_a`](https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeStockCount?node=hs_a)
- [`Market_Center.getHQNodeData` 的 5 行样本](https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeData?page=1&num=5&sort=symbol&asc=1&node=hs_a&symbol=&_s_r_a=page)

现场事实：

- `hs_a`、`sh_a`、`sz_a` 计数分别返回字符串 `5533`、`2309`、`2893`；
- `hs_a` 按代码升序的首行是 `bj920000`，因此该节点现场包含北交所证券；
- 每行现场包含 `symbol/code/name/trade/pricechange/changepercent/settlement/open/high/low/volume/amount/ticktime` 等字段；
- 5 行响应没有交易日期、时区、交易状态、分页总数或 universe 版本；
- 周日响应中的 `ticktime` 仍是上一交易日的时刻，仅凭 HTTP `Date` 无法证明行情所属交易日；
- `sh_a` 与 `sz_a` 的尾部时刻现场不同，不能把各行 `ticktime` 假设为同一截面时间。

结论是 **NO-GO**：接口可用于有界研究，不足以支撑可审计盘中产品合同。当前仓库已经把新浪候选源定位为未文档化、低频、本地研究展示；市场温度不应把这个风险放大为全市场持续扫描。

### 东方财富匿名网页接口

2026-08-02 对东方财富自有 `push2.eastmoney.com` 发出一页 5 行请求。现场响应有 `rc=0`、`data.total=5545`、5 行 `diff` 和 `f124` 数值时间戳；部分未开始交易或无行情记录的价格字段为字符串 `"-"`。候选请求：

[`clist/get` 5 行样本](https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&po=1&np=1&fltt=2&invt=2&fid=f12&fs=m%3A0%2Bt%3A6%2Cm%3A0%2Bt%3A80%2Cm%3A1%2Bt%3A2%2Cm%3A1%2Bt%3A23&fields=f12%2Cf13%2Cf14%2Cf2%2Cf3%2Cf4%2Cf18%2Cf17%2Cf15%2Cf16%2Cf5%2Cf6%2Cf124)

但本研究没有找到该网页接口的第一方公开字段字典、筛选表达式合同、证券纳入规则、版本、SLA 或再分发授权。`f2/f3/f18/f124` 的经济含义不能只靠值形状猜测。现场 `total=5545` 也与新浪 `hs_a=5533` 不一致，且样本包含多个价格为 `"-"` 的记录。

结论同样是 **NO-GO**：不把匿名、未文档化的 `f*` 字段引入后端领域模型。

## 市场温度精确计算合同

### 原始输入

对 universe 中每个成员，领域计算只接受：

- `symbol`：规范证券身份；
- `session_date`：上海时区下的交易日；
- `previous_close`：提供方针对本交易日给出的昨收/除权参考价；
- `last_price`：盘中最新成交价，或日终收盘价；
- `quote_at`：盘中必须包含日期、时间和时区；日终包使用 `session_date`，不得伪造逐行 15:00 时间；
- `trading_status`：若提供方正式定义；未知不能猜成停牌；
- `provider_change_percent`：只作交叉校验，不替代后端计算。

使用十进制定点数计算：

```text
delta = last_price - previous_close
change_ratio = delta / previous_close
```

`previous_close <= 0`、价格缺失、非有限数、身份不在 universe、日期不一致或盘中时间不可解释时，该成员不能进入涨跌分桶。除权日必须使用当日行情合同中的 `previous_close`；不得直接拿前一个日线文件的原始 `close` 替代。

### 涨、跌、平与 unavailable

| 分类 | 精确定义 |
|---|---|
| `advancers` | `delta > 0` |
| `decliners` | `delta < 0` |
| `unchanged` | 按来源原始价格精度比较后 `delta == 0`；不使用一个任意的涨跌幅 epsilon 把小涨跌归零 |
| `unavailable` | universe 成员无法得到合法 `previous_close/last_price` 或无法解释状态；包括 `NO_TRADE_YET`、`SUSPENDED`、`MISSING_QUOTE`、`INVALID_PRICE`、`NO_REFERENCE_PRICE`、`DATE_MISMATCH`，但只有来源能证明时才使用具体原因 |

上市首日如果没有合法的 `previous_close`，归为 `NO_REFERENCE_PRICE`，不进入涨、跌、平。全天停牌若没有最新成交价，归为 `SUSPENDED`；不能因为行情商返回昨收或零成交就自动算“平”。

### 12 个分桶

零涨跌由 `unchanged` 单独统计，不进入柱状分桶。所有非零有效 `change_ratio` 恰好进入一个桶：

| `id` | 数学边界 |
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

必须通过以下不变量：

```text
sum(bin.count) == advancers + decliners
advancers + decliners + unchanged == classified
classified + unavailable == universe_total
0 <= classified <= universe_total
```

### 覆盖率与质量状态

```text
coverage_ratio = classified / universe_total
resolution_ratio = (classified + explicitly_unavailable) / universe_total
```

`explicitly_unavailable` 是有来源状态或可验证原因的 unavailable；未知缺行不属于它。推荐状态合同：

| 状态 | 条件 | 页面行为 |
|---|---|---|
| `COMPLETE` | universe 和行情同一交易日；所有成员被唯一 join；`resolution_ratio=1`；所有不变量通过 | 展示分桶，同时显示 `classified/unavailable/coverage_ratio`；`unavailable` 可以非零 |
| `PARTIAL` | 核心日期与不变量通过，但存在少量未知缺行；`resolution_ratio >= 0.995` | 可展示，但必须显著标记部分覆盖和缺失原因，不得只写“已更新” |
| `FAILED` | `resolution_ratio < 0.995`、上游失败或没有足够有效成员 | 不展示可能误导的柱状分布；保留最近成功快照时必须明确标旧 |
| `REJECTED` | universe/行情日期错配、重复身份、未知交易所、负价格、分桶不变量失败、盘中时间倒退或来源合同漂移 | fail closed，不回退到零、演示数或匿名源 |

`0.995` 是建议的 **版本化产品阈值**，不是交易所事实。实现时应写入 `quality_policy_version`，修改阈值必须产生可审计版本变更。

### 盘中特有 fail-closed 条件

- 响应没有 `session_date`，且不能从有合同的 `trade_time` 解析；
- 任一批次的交易日不同；
- `snapshot_completed_at - snapshot_started_at` 超出版本化最大窗口；
- 行级最早/最晚行情时间偏差超出版本化阈值；
- 午间休市被标成持续更新，或收盘后继续返回无法解释的未来时间；
- 价格/涨跌幅系统性不一致；
- universe 总数突然变化但没有新的 universe 版本；
- 上游字段、分页或全量语义漂移。

## 推荐的后端深模块与 adapter seam

对路由暴露一个小 interface，而不是让路由、缓存和前端理解行情商字段：

```python
class MarketBreadthModule(Protocol):
    def get_snapshot(
        self,
        market: MarketId,
        mode: BreadthMode,
        as_of: date | None = None,
    ) -> MarketBreadthSnapshot: ...
```

这个 module 的 implementation 内部拥有：universe 版本选择、行情读取、规范身份 join、Decimal 计算、12 桶、不变量、覆盖率、状态、缓存和错误归一化。路由只序列化 `MarketBreadthSnapshot`，前端只格式化和绘图。

内部存在两个真实 adapter seam：

```python
class UniverseAdapter(Protocol):
    def load(self, market: MarketId, as_of: date) -> UniverseSnapshot: ...

class BreadthQuoteAdapter(Protocol):
    def load(self, universe: UniverseSnapshot, mode: BreadthMode) -> QuoteBatch: ...
```

建议的具体 adapter：

- `AuditableUniversePackageAdapter`：读取 Git 外、带 manifest 与哈希的 universe；
- `AuditableEodQuotePackageAdapter`：读取 Git 外逐证券日终原始行；
- `TushareRtKQuoteAdapter`：只有正式权限和动态合同通过后启用；
- 测试 fake：只通过相同 interface 提供固定 universe/quote batch，不在生产失败时自动回退。

`TushareDailyAdapter` 可作为**构建期工具**生成审计包，但默认运行时不应每次页面请求都重新抓全市场。运行时首先读取已经原子写入、校验成功的最新快照；刷新器在后台完成新包、校验、再切换指针，避免用户看到半批数据。

### 日终审计包建议

原始输入和凭证都留在 Git 外：

```text
market-breadth-package/
├── manifest.json
├── universe.csv
└── quotes.csv
```

`manifest.json` 至少包括：

- `schema_version`、`market`、`session_date`、`timezone`、`mode=EOD`；
- universe 与行情的正式来源、请求参数摘要、抓取开始/完成时间；
- 纳入/排除规则、提供方权限/许可备注；
- 两个 CSV 的行数、字节数与 SHA-256；
- 计算政策版本、预期 universe 数、可用数和 unavailable 原因计数。

`universe.csv` 保存逐成员身份与状态，`quotes.csv` 保存逐成员原始价格输入。聚合结果可以缓存，但不能只保留 12 个桶后丢失重算证据。仓库只提交 schema、校验器、测试 fixture 和不含真实市场数据的最小示例。

## 现场响应摘要与哈希

所有原始响应只临时存放在 `/tmp`，未进入 Git。现场日期均为 2026-08-02，网络响应时间约 14:49–14:53（Asia/Shanghai）。

| 一手对象 | 有界响应摘要 | SHA-256 |
|---|---|---|
| 上交所主板 A 股官方查询首 5 行 | 6380 bytes；`total=1698`；首行 `600000` 浦发银行 | `88be9401ede2f5bde6da7296d4595f9350e3fd7c856608ff25082ee38234f0de` |
| 上交所科创板官方查询首 5 行 | 6247 bytes；`total=612`；首行 `688001` 华兴源创 | `d22f9c00519446d2c17de7872f451c99c163cc47d10a1d56c4b9076c86ac983a` |
| 深交所 A 股列表官方 JSON 第 1 页 | 21476 bytes；`subname=2026-07-31`；`recordcount=2893` | `1b0e4b15eb1ead215da9602f7f401a96fb27c1ffe1c95ace214c0617a8970be5` |
| Tushare `stock_basic` 文档 HTML | 当前列表、权限、单次全量说明 | `15ee260b96477ece249ba9a75b68b94e8b82d10e584bf15958ff6dc4bf567e55` |
| Tushare `daily` 文档 HTML | 15–16 点入库、6000 条、停牌无数据、价格字段 | `37590928ede332655bcd56f9fe37f93694ebe1ef9db8b204ec693d385d4cb0ff` |
| Tushare `rt_k` 文档 HTML | 全市场实时日 K、6000 条、单独权限 | `9820bfa4a5f64c245fbdf74d0dbdcfdc7af6942ef2b3f3e36f0e32e9b8e683c9` |
| Tushare `rt_min` 文档 HTML | 多代码、1000 行、需权限 | `64fad6c8f039802187f87ba495f86a8d5acc630e73aa972a2f153b1eceb6d52a` |
| Tushare 无 Token 请求 | 80 bytes；`code=40101`、`data=null` | `fb791f8d8be3375e347ad867d39c46af62ea2906bea7dfbb25a48c806735cc8e` |
| 新浪 `hs_a` count | JSON 字符串 `"5533"`，6 bytes | `143dae5a52d65fca633a5755316dcdc301b0a7c0d5d2b401e8b5a83acda5b9cc` |
| 新浪 `sh_a` count | JSON 字符串 `"2309"`，6 bytes | `546a527fc56f9ca6629178e4174a51dac094b2163b64c370dbd584c24e64162c` |
| 新浪 `sz_a` count | JSON 字符串 `"2893"`，6 bytes | `9d2a0d057031e28344bebece3b90d8b806327ca3bafb051dc7ac8cee6a54db45` |
| 新浪 `hs_a` 5 行 | 1854 bytes；首行 `bj920000`；有时刻无日期 | `8ef9ee82fe29c3096e5bfaa33299151fca3fea64973020ef96b649f6c87b6984` |
| 东方财富候选 5 行 | 897 bytes；`total=5545`；部分价格为 `"-"` | `aad142efc7030aa125b8d54d70615eca328bcca77c2004b979c95cd5f0ae4b9b` |

哈希只证明本次看到的字节内容，不能把匿名响应升级为稳定合同，也不能证明数据准确、授权或未来不变。

## 下一步门槛

### 可以立即进入设计/测试的内容

- 将产品范围明确扩展为 `CN_A_SH_SZ_V1` **日终市场温度**；
- 测试先行实现纯领域计算、不变量和审计包 schema；
- 只用合成 fixture 验证边界值，不把 fixture 展示成真实市场；
- 由用户在 Git 外提供一份合法日终 package 后做端到端验收。

### 仍需新授权或真实交易时段的内容

- 使用 Tushare Token、购买/检查 `daily` 或 `rt_k` 权限；
- 自动从外部提供方下载完整市场数据；
- 对盘中 `rt_k` 做开盘、午休、下午恢复和收盘动态核验；
- 开启任何对匿名网页接口的全市场周期扫描；
- 把北交所加入当前 `.SH/.SZ` 身份合同。

若没有正式数据权限，首版的正确落点是 **可审计日终文件模块**；若用户要求现在就上线匿名盘中版，则本研究结论保持 **NO-GO**。
