# Chan Quant

缠论量化研究台。项目目标是把分型、笔、通道、买卖线与多周期状态转换为可复现、可审计且不使用未来数据的研究系统。

当前处于初始架构阶段。真实策略公式尚未确认，界面和 API 中只能使用明确标注的 mock 数据。

## 本地运行

启动 mock API：

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

打开 `http://127.0.0.1:5173/`。页面顶部会明确显示 mock 数据警告。

## 验证

```bash
cd backend
uv run ruff check .
uv run pytest -q

cd ../frontend
npm test
npm run build
```

产品范围、规则状态与 API 合同见 `docs/`。

## 边界

- 研究和可视化优先，不连接券商或自动下单。
- 策略事件分别记录结构时间、确认时间与最早可执行时间。
- 页面展示与策略计算分离，前端不得重新实现交易规则。
- 行情、凭证、API Token 与本地缓存不提交到 Git。
