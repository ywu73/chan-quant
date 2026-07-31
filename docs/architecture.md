# 系统架构

```text
确定性合成数据 / 本地 CSV / 新浪未文档化 K 线端点
  -> MarketBar 规范化与时序校验
  -> EMA/SMA/Donchian/日周趋势
  -> 严格三 K 分型与简化笔
  -> setup 生命周期与候选信号
  -> next-open 事件研究
  -> Dashboard API ───────────────────────┐
                                          ├─> React + ECharts
新浪未文档化实时快照 -> QuoteSnapshot     │
  -> 独立 Quote API ──────────────────────┘
```

## 模块边界

- `backend/src/chan_quant/domain`：稳定领域数据模型与时间约束。
- `backend/src/chan_quant/data`：CSV、新浪 K 线与新浪实时快照适配、代码映射、输入和上游错误归一化。
- `backend/src/chan_quant/audit`：候选行情与参考日线、交易日历及历史快照的可复现质量审计。
- `backend/src/chan_quant/strategy`：指标、结构和 Independent v0.1 信号引擎。
- `backend/src/chan_quant/backtest`：无成本的信号事件研究，不是组合回测。
- `backend/src/chan_quant/services`：合成行情生成与 Dashboard 快照组装。
- `backend/src/chan_quant/api`：HTTP 适配层，不包含策略规则。
- `frontend/src/api`：Dashboard 与 Quote 快照获取及错误处理。
- `frontend/src/quotePolling.ts`：8 秒低频轮询、页面可见性暂停和生命周期清理。
- `frontend/src/components`：纯展示组件和图表。

后端是策略事实的唯一所有者。前端只消费快照，不能重新计算均线、多空、共振、信号或事件成功率。

新浪端点不允许前端直连。后端负责请求和 GB18030 兼容解码：K 线 JSON 归一化为 `MarketBar`，实时赋值语句归一化为 `QuoteSnapshot`。两条链路只在页面展示层并列，Quote 模块不接受 `MarketBar`、不调用策略引擎，也不写回 Dashboard。外部响应中的均线字段和盘中价格都不参与策略计算。

审计模块负责对照原始日线、公司行动、交易日历和重复快照；审计结论由后端生成，不在前端重新推导，也不会把实时 Quote 引入日线策略。

实时状态也由后端给出。前端只把 `LIVE/DELAYED/CLOSED` 格式化为“实时/延迟/已收盘”，请求失败则明确显示“不可用”；失败时旧价会被清除，日线 Dashboard 继续工作。

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
