# 系统架构

```text
确定性合成数据 / 本地 CSV / 可审计历史快照 / 新浪未文档化 K 线端点
  -> MarketBar 规范化与时序校验
  -> EMA/SMA/Donchian/日周趋势
  -> 严格三 K 分型与简化笔
  -> setup 生命周期与候选信号
  -> next-open 事件研究
  -> Dashboard API ───────────────────────┐
                                          ├─> React + ECharts
新浪未文档化实时快照 -> QuoteSnapshot     │
  -> 独立 Quote API ──────────────────────┘

新浪未文档化证券建议 -> InstrumentIdentity
  -> 独立 Search / Identity API -> 初始页 / Dashboard 标的切换 / 比较板块身份

新浪未文档化 K 线端点 -> ComparisonInput[]
  -> 共同覆盖窗口与交易日并集对齐
  -> 起始价 / 区间末收盘 / 上一交易日涨幅 / 归一化收益 / 累计收益 / 最大回撤
  -> Market Comparison API -> 多标的走势对比页 / 固定指数表现页 <- 独立多标的 Quote 轮询

上交所 JSON + 深交所 XLSX -> 远端沪深 A 股 universe
  -> 新浪逐证券行情 / 提供方 session_date / 5 分钟进程内缓存
  -> Decimal 涨跌分类 / 12 桶 / 覆盖率 / 质量状态
  -> Market Breadth API -> 首页沪深 A 股远端市场温度
```

## 模块边界

- `backend/src/chan_quant/domain`：稳定领域数据模型与时间约束。
- `backend/src/chan_quant/data`：CSV、新浪 K 线、实时快照与标的元数据适配、代码映射、输入和上游错误归一化。
- `backend/src/chan_quant/data/market_snapshot.py`：仓库外 `manifest.json + bars.csv` 的联合加载、SHA-256、标的、周期、日期范围和根数校验；失败时禁止降级。
- `backend/src/chan_quant/data/market_breadth_package.py`：仓库外 `manifest.json + universe.csv + quotes.csv` 的联合加载、字节数、SHA-256、身份、行数和日期校验；失败时禁止降级。
- `backend/src/chan_quant/data/exchange_universe_source.py`：上交所官方 JSON 与深交所官方 XLSX 的远端 universe adapter；统一规范证券身份、板块和上市日期，并拒绝不完整列表。
- `backend/src/chan_quant/data/sina_market_breadth_source.py`：未文档化新浪批量行情的 GB18030 传输与逐行日期/身份解析 adapter；同时供远端观测和显式离线导入使用。
- `backend/src/chan_quant/data/remote_market_breadth.py`：远端市场温度深模块；把交易所 universe、新浪行情、交易日过滤、60 秒抓取窗口、300 秒成功缓存、强制刷新和来源风险隐藏在单一 `get()` 接口后。
- `backend/src/chan_quant/importers/sina_market_breadth.py`：把用户提供的官方同日 universe、逐批新浪响应和原始 evidence 原子转换为 v0.2 审计包；完整重读通过前不更新 `current`。
- `backend/src/chan_quant/domain/market_breadth.py`：稳定的沪深 A 股 universe、日终或远端逐证券观察、12 个分桶、覆盖率、质量状态与拒绝合同。
- `backend/src/chan_quant/domain/data_quality.py`：稳定的数据清单、数据集身份、完整性状态、复权依据和 reason code 合同。
- `backend/src/chan_quant/domain/instrument.py`：稳定标的身份，包括规范代码、名称、交易所、可确认的资产类别与价格精度。
- `backend/src/chan_quant/audit`：候选行情与参考日线、交易日历及历史快照的可复现质量审计。
- `backend/src/chan_quant/strategy`：指标、结构和 Independent v0.1 信号引擎。
- `backend/src/chan_quant/backtest`：无成本的信号事件研究，不是组合回测。
- `backend/src/chan_quant/services`：合成行情生成与 Dashboard 快照组装。
- `backend/src/chan_quant/services/market_comparison.py`：多标的取数 seam 后的日期过滤、共同窗口、缺失日对齐、历史价格、上一交易日涨幅、归一化收益、累计收益、最大回撤与逐项失败隔离。
- `backend/src/chan_quant/services/market_breadth.py`：后端唯一的涨跌分类、非零分桶、不变量、覆盖率、可解释比例和质量状态所有者。
- `backend/src/chan_quant/api`：HTTP 适配层，不包含策略规则。
- `frontend/src/api`：Dashboard 与 Quote 快照获取及错误处理。
- `frontend/src/components/InstrumentSearch.tsx`：标的输入、搜索建议和选择交互，不计算策略规则。
- `frontend/src/marketInstruments.ts`：经过现有身份适配器现场确认的共享市场标的目录；保留提供方无法确认的 `UNKNOWN` 资产类别。
- `frontend/src/comparisonBoards.ts`：内置板块成员与来源证据、板块身份、数量、版本化存储解析、未知版本保留和损坏数据隔离。
- `frontend/src/useComparisonBoards.ts`：浏览器本地板块存储的生命周期与变更编排，展示组件不直接访问 `localStorage`。
- `frontend/src/quotePolling.ts`：8 秒低频轮询、页面可见性暂停和生命周期清理。
- `frontend/src/comparisonQuotePolling.ts`：多标的 Quote 并发、逐项失败、请求取消、页面可见性和晚到结果抑制的深模块；外部 interface 只有启动与停止。
- `frontend/src/useComparisonQuotes.ts`：把多标的 Quote 更新映射为 React 页面状态，不实现行情计算或请求编排。
- `frontend/src/components/ComparisonMetricCard.tsx`：并列展示后端历史指标与独立 Quote 状态，不让盘中价覆盖历史结论。
- `frontend/src/indexPerformance.ts`：只负责本地日历日期区间和快捷选项，不计算任何历史收益或回撤。
- `frontend/src/components/IndexPerformancePage.tsx`：编排 8 个共享沪深宽基身份的比较请求与独立 Quote 状态；固定卡片顺序，逐项失败隔离。
- `frontend/src/components/IndexPerformanceCard.tsx`：并列格式化后端历史指标与当前行情，明确区分区间末收盘和独立 Quote。
- `frontend/src/components/MarketBreadthPanel.tsx`：只渲染后端聚合结果、审计身份和失败状态；覆盖不足时隐藏分布，不从行情行重新计算。
- `frontend/src/components`：纯展示组件和图表。

后端是策略事实的唯一所有者。前端只消费快照，不能重新计算均线、多空、共振、信号或事件成功率。

多标的比较同样由后端拥有研究计算。统一日期轴是成功序列共同覆盖窗口内的交易日并集；某个标的缺少的日期返回 `null`，不以前值、零或其他标的价格填充。每条序列使用窗口内首个有效收盘价归一化，起始价、区间末收盘、上一交易日涨幅、累计收益和最大回撤均由后端给出，前端只格式化与绘图。

内置板块是前端的静态选择 preset，不是新的行情或计算数据源。`comparisonBoards.ts` 以一个嵌套的成员证据 interface 隔离来源差异：宽基目录记录全量核验规则；行业/主题观察组记录中证官方指数、成员归属日、精确权重排序、官方权重响应与同日成分文件哈希。运行时只把既有规范身份装入后端比较请求，后端仍独立校验 2–8 个不同代码并拥有全部走势计算。官方权重不参与曲线计算，也不把八个标的提升为完整指数或可交易组合。

可审计历史快照把数据身份与计算视图分开：`dataset_id` 由规范化 manifest 生成，`as_of` 只截断本次策略计算所见的 K 线，不改变数据集身份或完整数据范围。文件哈希、manifest 或任何一根 K 线变化都会形成不同身份或直接因哈希不匹配而失败。`provider-declared` 只记录提供方声明，不会被提升为独立复权审计结论。

市场温度是独立于单标的策略和 Quote 的远端观测链路。运行时从交易所列表建立分母，并使用新浪当日参考昨收和最新价复算方向、零涨跌、12 个非零分桶和覆盖率。前端只允许根据后端 `COMPLETE/PARTIAL/FAILED` 状态决定是否渲染，不能从逐证券行情重新聚合，也不能把远端观测包装成审计快照。

远端市场温度模块是页面与三个外部来源之间的 seam。普通读取复用 300 秒进程内缓存；显式刷新重新访问交易所和新浪，失败不回退到旧值。未文档化来源与无持久证据分别由后端附加 `SINA_UNDOCUMENTED_SOURCE` 和 `REMOTE_OBSERVATION_NOT_AUDITABLE`，前端只显示风险，不自行推断数据合同。新浪导入器继续作为独立离线证据工具，但其输出不再是页面依赖。

新浪端点不允许前端直连。后端负责请求和 GB18030 兼容解码：K 线 JSON 归一化为 `MarketBar`，实时赋值语句归一化为 `QuoteSnapshot`。两条链路只在页面展示层并列，Quote 模块不接受 `MarketBar`、不调用策略引擎，也不写回 Dashboard。外部响应中的均线字段和盘中价格都不参与策略计算。

标的名称搜索和规范代码身份解析同样只允许后端访问新浪未文档化建议端点。适配器在同一个深模块中完成类型过滤、代码规范化、精确身份解析和价格精度选择：现场类别 `203` 标记为 `ETF` 并使用三位价格，类别 `11` 因可能包含股票与指数别名而保留为 `UNKNOWN`。搜索结果只决定用户选择的 Dashboard URL 或比较组合身份，不生成信号、推荐或全市场扫描结论。元数据查询失败时，Dashboard 回退显示请求中的规范代码和未知口径；自定义板块则拒绝把前端猜测的名称、类型或精度保存为稳定身份。

Dashboard 和 Quote 展示以 `InstrumentIdentity` 为稳定身份。Quote 响应中的名称保留为上游原始字段，但不能覆盖 Dashboard 主标题，因为新浪实时接口可能对 ETF 返回简称。ETF 日 K 可以进入现有策略计算，但使用 `adjustment=unspecified` 和独立风险提示；三只股票样本的复权观察不得外推到 ETF。

审计模块负责对照原始日线、公司行动、交易日历和重复快照；审计结论由后端生成，不在前端重新推导，也不会把实时 Quote 引入日线策略。

实时状态也由后端给出。前端只把 `LIVE/DELAYED/CLOSED` 格式化为“实时/延迟/已收盘”，请求失败则明确显示“不可用”；失败时旧价会被清除，日线 Dashboard 和历史比较继续工作。多标的 Quote 使用一个共享轮询模块管理最多八个独立请求，页面隐藏或组合失效时中止当前周期，恢复可见后重新开始；任何晚到响应都不能写回已经停止的周期。

## 时间与前缀稳定性

计算始终按日期升序，只使用当前索引及之前可见的数据：

1. Donchian 上下沿排除当前 K 线；
2. 分型在右侧 K 线收盘后确认；
3. 周线状态只读取上一完整周；
4. 信号条件在触发根收盘后确认；
5. 事件执行使用下一根已存在 K 线开盘；
6. setup 在相反分型确认时关闭，不使用未来结构回删既有信号。

自动测试逐一截取所有有效历史前缀，验证信号身份、结构索引和确认索引不会被后续 K 线改写。唯一允许的前沿变化是：数据停在确认根时执行索引为空，下一根 K 线到来后补充其开盘索引。

## 明确缺失的层

v0.1 没有 K 线包含处理、中枢、背驰、受支持的正式行情 SDK、复权引擎、交易成本、持仓状态机或资金曲线。新浪适配器只是未文档化候选数据源；`unadjusted-observed` 是三标的有限现场证据，不是上游固定合同，也不会消除除权跳变。缺失能力不能通过前端展示层补算，也不能以参考截图的术语暗示已经实现。

## 演进顺序

1. 固定 Independent v0.1 规则、页面与 API 合同；
2. 用人工小样例和前缀测试审计结构、指标和时间逻辑；
3. 接入经过许可的真实历史数据源并明确复权口径；
4. 增加交易成本和市场规则后，才实现持仓与组合回测；
5. 进行样本外验证后，再单独决定是否讨论模拟盘。
