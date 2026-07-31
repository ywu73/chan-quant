# Chan Quant

Chan Quant 是一个结构与趋势量化研究台。它把严格三 K 分型、简化笔、均线、Donchian 通道、多周期状态和候选信号转换为可复现、可审计且不使用未来数据的计算结果。

当前策略版本为 **Independent v0.1 草案**。它是本项目独立选择的一套工程规则，不是参考截图作者的原始公式，也不声称是“标准”或“正统”缠论。系统仍是研究与审计工具，不提供实盘交易能力。

## 本地运行

启动 API。未配置行情文件时，后端使用确定性合成数据，并在响应和页面中明确标记：

```bash
cd backend
uv sync --all-groups
uv run uvicorn chan_quant.api.app:app --host 127.0.0.1 --port 8000
```

另开一个终端启动页面：

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

打开 `http://127.0.0.1:5173/`。

### 使用本地 CSV

CSV 至少需要 `trade_date`（或 `date`）、`open`、`high`、`low`、`close`、`volume` 六列，可选 `amount`。Independent v0.1 的 EMA90 预热要求至少 92 根有效日 K：

```bash
cd backend
CHAN_QUANT_CSV_PATH=/absolute/path/to/bars.csv \
CHAN_QUANT_ADJUSTMENT=qfq \
CHAN_QUANT_INSTRUMENT_NAME='研究标的' \
uv run uvicorn chan_quant.api.app:app --host 127.0.0.1 --port 8000
```

`CHAN_QUANT_ADJUSTMENT` 只记录数据提供方声明的复权口径，程序不会自行推断或复权。接入 CSV 后 `is_mock=false`，但策略规则状态仍为 `DRAFT`，不能据此宣称已经验证有效。

### 使用新浪财经候选 K 线源

新浪端点目前不需要 Token，但没有公开字段合同、复权说明或 SLA。本项目只从 Python 后端低频访问日 K 和单标的实时快照；实时快照使用独立接口和页面区域，**不进入策略链路**：

```bash
cd backend
CHAN_QUANT_DATA_SOURCE=sina \
CHAN_QUANT_SINA_DATALEN=2000 \
CHAN_QUANT_INSTRUMENT_NAME='平安银行' \
uv run uvicorn chan_quant.api.app:app --host 127.0.0.1 --port 8000
```

前端启动后打开：

```text
http://127.0.0.1:5173/?symbol=000001.SZ
```

新浪模式只支持 `NNNNNN.SZ` 和 `NNNNNN.SH`。响应会明确标记：

```text
data_source = sina-undocumented-kline
adjustment = unknown
strategy.rule_status = DRAFT
```

现场观测、访问限制和使用边界见 `docs/sina-data-source.md`。

### 独立实时行情

无论 Dashboard 使用合成数据、CSV 还是新浪日 K，规范沪深代码的页面都会通过后端独立访问：

```http
GET /api/v1/instruments/000001.SZ/quote
```

前端每 8 秒低频轮询；页面隐藏时暂停，重新可见时立即刷新。实时区域显示最新价、涨跌、开高低、成交量、行情时间、接收时间、数据源和 `实时/延迟/已收盘/不可用` 状态。上游失败只会让实时区域进入不可用状态，不会阻断 Dashboard。

`quote_at` 来自新浪响应，`received_at` 是后端接收时间。两者不得互相替代。实时价不会写入日 K，也不会改变 Independent v0.1 的 EMA、Donchian 通道、分型、简化笔、候选信号或事件研究。

## 验证

```bash
cd backend
uv run ruff check .
uv run pytest -q

cd ../frontend
npm test
npm run build
```

规则口径、数据合同、架构和产品边界见 `docs/`。

## 边界

- 研究和可视化优先，不连接券商或自动下单。
- 策略事件分别记录结构时间、确认时间与最早可执行时间。
- 页面展示与策略计算分离，前端不得重新实现交易规则。
- 合成数据上的信号数量和事件统计只验证计算链路，不代表真实市场表现。
- 新浪实时快照是未文档化 HTTP 端点的低频展示，不是 WebSocket、交易行情 SLA 或实盘性能证据。
- 匿名可访问不等于获得商业使用、再分发或稳定服务授权。
- 当前没有交易成本、滑点、涨跌停、停牌、分红处理或组合资金曲线。
- 行情、凭证、API Token 与本地缓存不提交到 Git。
