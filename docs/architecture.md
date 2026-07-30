# 系统架构

```text
确定性合成数据 / 本地 CSV
  -> MarketBar 规范化与时序校验
  -> EMA/SMA/Donchian/日周趋势
  -> 严格三 K 分型与简化笔
  -> setup 生命周期与候选信号
  -> next-open 事件研究
  -> FastAPI 快照
  -> React + ECharts
```

## 模块边界

- `backend/src/chan_quant/domain`：稳定领域数据模型与时间约束。
- `backend/src/chan_quant/data`：CSV 行情适配与输入错误归一化。
- `backend/src/chan_quant/strategy`：指标、结构和 Independent v0.1 信号引擎。
- `backend/src/chan_quant/backtest`：无成本的信号事件研究，不是组合回测。
- `backend/src/chan_quant/services`：合成行情生成与 Dashboard 快照组装。
- `backend/src/chan_quant/api`：HTTP 适配层，不包含策略规则。
- `frontend/src/api`：快照获取与错误处理。
- `frontend/src/components`：纯展示组件和图表。

后端是策略事实的唯一所有者。前端只消费快照，不能重新计算均线、多空、共振、信号或事件成功率。

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

v0.1 没有 K 线包含处理、中枢、背驰、真实行情 SDK、复权引擎、交易成本、持仓状态机或资金曲线。它们不能通过前端展示层补算，也不能以参考截图的术语暗示已经实现。

## 演进顺序

1. 固定 Independent v0.1 规则、页面与 API 合同；
2. 用人工小样例和前缀测试审计结构、指标和时间逻辑；
3. 接入经过许可的真实历史数据源并明确复权口径；
4. 增加交易成本和市场规则后，才实现持仓与组合回测；
5. 进行样本外验证后，再单独决定是否讨论模拟盘。
