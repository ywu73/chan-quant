# Dashboard API 数据契约

## 快照接口

```http
GET /api/v1/instruments/{symbol}/dashboard?timeframe=1d&as_of=2026-07-30&lookback=2y
```

当前实现只返回 `DEMO.SZ` 的确定性 mock 快照，并在响应中设置：

```json
{
  "is_mock": true
}
```

## 核心约束

- 后端拥有全部策略计算和状态判断。
- 前端只格式化后端值，不重新判断多空、共振或操作结论。
- 所有比例使用十进制传输，例如 `-0.2085` 在页面格式化为 `-20.85%`。
- 所有日期使用 ISO 8601。
- `headline_total = buy_total + sell_total + excluded_total`。
- 每个周期满足 `successes <= eligible <= total_signals`。
- 每个信号满足 `structure_at <= confirmed_at <= executable_at`。

## 版本字段

快照必须包含 `strategy.version` 与 `strategy.parameter_version`。未来任何规则或参数变化都必须产生新版本，避免相同日期的历史结果被静默改写。
