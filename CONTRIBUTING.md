# 贡献指南

感谢你关注 Chan Quant。这个仓库是一个 **Experimental / Research Preview** 阶段的可审计量化研究项目。维护者会选择性处理 Issue 和 Pull Request，不承诺响应时限。

## 可接受的贡献

- 可复现的缺陷修复与回归测试；
- 指标、结构状态、信号和事件研究的时间正确性改进；
- 数据合同、来源证据、失败语义和质量提示改进；
- 不改变后端计算所有权的前端可访问性与交互改进；
- 文档、测试、构建和依赖维护。

以下内容不属于当前项目范围：

- 券商连接、自动下单、公开交易信号或实盘凭证；
- 未定义或无法提供来源的买卖线、中枢、背驰、共振等公式；
- 真实行情文件、原始响应、Cookie、Token、授权材料或个人账户数据；
- 把合成数据、事件研究或回测描述为真实交易表现；
- 未经授权复制的闭源指标、商业策略、付费内容或第三方数据。

## 开始开发

后端要求 Python 3.10 或更高版本，并使用 `uv`：

```bash
cd backend
uv sync --locked --all-groups
uv run ruff check .
uv run pytest -q
```

前端使用 Node.js 22 或兼容版本：

```bash
cd frontend
npm ci
npm test
npm run build
```

测试不得访问新浪、交易所或其他真实行情端点。请使用 mock、fixture 或确定性合成数据。

## 架构与时间规则

- Python 后端拥有指标、结构状态、信号、事件研究和策略结论；前端只负责格式、布局、图表和交互。
- 结构事件必须区分 `structure_at`、`confirmed_at` 和 `executable_at`。
- 已确认历史信号必须通过 prefix-stability 测试，不能被未来 K 线静默改写。
- 图表可以把结构画在枢轴 K 线上，但交易模拟只能使用第一根实际可执行 K 线。
- 不支持或无效的数据模式应明确失败，不能静默回退到其他来源。

详细边界见 [`AGENTS.md`](AGENTS.md)、[`docs/architecture.md`](docs/architecture.md) 和 [`docs/data-contract.md`](docs/data-contract.md)。

## 提交 Issue

普通缺陷和功能建议使用仓库 Issue 模板。安全漏洞、凭证或可利用细节不得提交到公开 Issue，请使用 GitHub Private Vulnerability Reporting。

## 提交 Pull Request

Pull Request 应说明：

- 变更动机和用户可见行为；
- 是否改变时间语义、数据合同或远端访问；
- 数据及第三方材料的来源和授权边界；
- 已运行的测试与未执行的验证；
- UI 变更的截图或录屏。

项目不要求 CLA 或 DCO。向本仓库有意提交贡献，表示你确认自己有权提交相应内容，并同意按 [Apache License 2.0](LICENSE) 提供该贡献。
