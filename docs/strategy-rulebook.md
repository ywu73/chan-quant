# 策略规则说明书

状态说明：`CONFIRMED` 表示已从参考界面可靠推导；`UNCONFIRMED` 表示仍需原始公式或人工样例。

## 已确认的展示公式

### 现价相对指标线（CONFIRMED）

```text
relative_to_line = current_price / line_value - 1
```

适用于买线、卖线与 MA57 卡片。

### 买卖线差（CONFIRMED）

```text
line_spread_pct = buy_line / sell_line - 1
line_spread_abs = buy_line - sell_line
```

### 历史胜率（CONFIRMED）

```text
success_rate = successes / eligible_signals
```

未来 5/10/20 日收益栏的汇总方式仍为 `UNCONFIRMED`。

## 待确认规则

| 规则 | 状态 | 需要的证据 |
|---|---|---|
| K 线包含关系 | UNCONFIRMED | 上升/下降包含处理及相等高低点样例 |
| 顶底分型 | UNCONFIRMED | 窗口、确认时点及冲突处理 |
| 成笔规则 | UNCONFIRMED | 最小间隔、延伸、替换和破坏规则 |
| 买线 | UNCONFIRMED | 完整公式、参数和输入价格 |
| 卖线 | UNCONFIRMED | 完整公式、参数和输入价格 |
| 短通道（24日） | UNCONFIRMED | 通道算法和多空切换条件 |
| 长通道（90日） | UNCONFIRMED | 通道算法和多空切换条件 |
| 日/周均线状态 | UNCONFIRMED | 均线组合、斜率和强度阈值 |
| 多周期 1/4 共振 | UNCONFIRMED | 四个组成条件及计分方式 |
| 顶/底背驰 | UNCONFIRMED | MACD 参数、比较区间及结构对应规则 |
| 一买/一卖 | UNCONFIRMED | 信号定义、确认时点及冷却规则 |
| 事件研究成功条件 | UNCONFIRMED | 执行价、成本、收益阈值及卖出含义 |

## 时间真实性契约

每个结构或信号必须记录：

```text
structure_at <= confirmed_at <= executable_at
```

- `structure_at`：结构在图上的归属时间；
- `confirmed_at`：使用当时可见数据首次确认的时间；
- `executable_at`：按照市场规则最早可执行的时间。

图表允许把分型画在枢轴 K 线上，但事件研究和回测只能使用 `executable_at` 对应的可成交价格。
