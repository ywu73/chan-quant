# 数据源注册表

## 定位

[`data-source-registry.json`](data-source-registry.json) 是当前外部与用户提供市场输入的机器可校验台账。它记录的是**能力级决策**，不是供应商级背书：同一供应商的日 K、Quote、搜索或市场温度必须分别登记，某一能力通过现场研究不能自动外推到其他能力。

注册表不选择运行时数据源，不保存凭证、真实行情、完整上游响应或授权材料，也不会把匿名可访问、官方公开页面或文件完整性提升为商业使用和再分发许可。运行时模式仍由现有环境变量和后端装配层决定。

## 决策字段

每条来源记录分别给出：

- `local_research`：是否能在当前证据边界内用于本地研究；
- `production_market_data`：是否具备生产行情合同、稳定性和运维证据；
- `commercial_use`：仓库是否已经建立商业使用权限证据；
- `redistribution`：仓库是否已经建立行情或主数据再分发权限证据；
- `automatic_fallback`：是否允许系统在主源失败后自动切换到该来源。

`GO` 只对对应字段和对应能力生效。`CONDITIONAL_GO` 表示仍有必须在使用前满足的外部条件；`PENDING` 表示研究尚未形成足够证据；`NO_GO` 表示当前不得把该能力用于相应范围。注册表结论是工程与产品闸门，不构成法律意见。

## 强制不变量

[`chan_quant.audit.data_source_registry`](../backend/src/chan_quant/audit/data_source_registry.py) 使用 Pydantic 拒绝不完整或自相矛盾的记录：

1. 远端来源必须只由后端访问，并受 `CHAN_QUANT_REMOTE_NETWORK_ENABLED` 总闸门控制；
2. 未文档化来源的许可状态必须保留为 `UNVERIFIED`；
3. 未文档化来源不得标记为生产行情、商业使用或再分发 `GO`；
4. 许可状态未验证的来源不能标记为生产、商业或再分发 `GO`，即使来源是官方公开页面；
5. v0.1 的所有来源都禁止自动 provider fallback；
6. 日 K 来源必须明确声明可观察或可请求的复权语义；非日 K 来源不得借用复权字段；
7. 每条记录必须引用至少一份仓库内证据文档，引用路径必须存在。

## 验证

在后端目录运行：

```bash
uv run pytest -q tests/test_data_source_registry.py
uv run ruff check src/chan_quant/audit/data_source_registry.py tests/test_data_source_registry.py
```

校验只证明注册表结构和项目政策一致，不会重新访问第三方接口，也不能证明记录中的外部来源仍然可用。

## 新增或更新来源

数据源状态变化时，必须在同一变更中：

1. 更新或新增一份引用一手来源的研究文档；
2. 按具体能力新增或更新注册表记录；
3. 更新 `last_verified_at`，保留带 `+08:00` 的现场核验时间；
4. 明确区分现场可访问、字段合同、复权经济含义、许可、SLA 和再分发；
5. 运行注册表测试；
6. 若准备接入运行时，再单独实现后端 adapter、合同测试和显式数据模式。

候选来源成为运行时来源、修改默认来源或改变失败/降级策略，均需要独立实现任务和新的明确授权，不能只通过修改本注册表完成。
