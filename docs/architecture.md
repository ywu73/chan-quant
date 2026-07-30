# 系统架构

```text
行情提供者
  -> 数据校验与复权
  -> 包含关系状态机
  -> 分型状态机
  -> 笔状态机
  -> 买卖线/通道/均线
  -> 信号与解释引擎
  -> 事件研究/组合回测
  -> FastAPI 快照
  -> React + ECharts
```

## 模块边界

- `backend/src/chan_quant/domain`：稳定领域数据模型与时间约束。
- `backend/src/chan_quant/services`：应用服务与 mock 快照；真实策略实现后替换数据来源。
- `backend/src/chan_quant/api`：HTTP 适配层，不包含策略规则。
- `frontend/src/api`：快照获取与错误处理。
- `frontend/src/components`：纯展示组件和图表。
- `fixtures/strategy-cases`：人工标注的正例、反例与时间确认案例。

## 演进顺序

1. 固定页面与 API 合同；
2. 收集原始公式和人工标注；
3. 实现结构状态机及前缀稳定性测试；
4. 实现指标与信号解释；
5. 实现事件研究；
6. 样本外验证后再讨论模拟盘。
