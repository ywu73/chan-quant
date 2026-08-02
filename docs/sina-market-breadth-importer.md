# 新浪日终市场温度审计包导入器

## 定位与边界

该导入器把用户提供的同日沪深 A 股官方 universe 与新浪网页行情端点的逐证券响应，转换为 Git 外的 `market-breadth-package-v0.2` 审计包。它是本地、低频、显式执行的离线证据工具，不是首页数据源、实时行情服务、定时抓取器或新浪正式 API 客户端。

新浪端点当前未找到公开开发者合同、字段版本、请求上限、SLA 或第三方使用与再分发授权。运行命令必须显式提供 `--acknowledge-undocumented-sina`；该确认只表示操作者理解工程风险，不表示已经取得授权。

导入器不会：

- 用新浪 `hs_a`、`sh_a` 或 `sz_a` 节点替代官方证券 universe；
- 参与首页运行时远端观测或缓存；
- 自动定时运行；
- 把空响应、零价格或缺失证券算成平盘；
- 在失败时覆盖上一份成功包；
- 把真实市场数据、原始响应或授权材料写入 Git。

## 前置合同探测

批次大小没有公开合同。首次运行前，应在一个真实开市日收盘后依次用 10、50、100 个非敏感证券代码做有界探测，核对：

1. HTTP 状态和最终 URL；
2. 请求证券与返回变量名一一对应；
3. 每条记录至少 32 个字段；
4. 每条记录都有同一个 `YYYY-MM-DD`；
5. 昨收和最新价是有限正数，或返回可解释的空记录；
6. 响应没有额外、重复或遗漏证券；
7. 没有 `403`、`429`、超时或结构漂移。

命令行的 `--batch-size` 是必填项，必须使用本次现场探测已经证明完整的数值。一次有界探测只能证明当时的响应行为，不能升级为新浪长期承诺。

## universe.csv

调用方必须提供 UTF-8 CSV，并对来源日期、合法使用边界和证券身份负责。固定表头：

```csv
symbol,exchange,security_name,security_type,board,list_date,delist_date
```

字段合同与 [`market-breadth-package.md`](market-breadth-package.md) 一致：

- `symbol` 为 `NNNNNN.SH` 或 `NNNNNN.SZ`；
- `exchange` 与代码后缀一致；
- `security_type` 固定为 `A_STOCK`；
- `board` 为 `MAIN`、`STAR` 或 `CHINEXT`；
- `list_date` 不晚于导入交易日；
- 已在该交易日生效退市的成员不得出现；
- universe 中不得重复证券。

第一版不自动抓取交易所列表。推荐将上交所、深交所官方同日导出在 Git 外固化后再运行导入器。

## 执行命令

```bash
cd backend

uv run python -m chan_quant.importers.sina_market_breadth \
  --session-date 2026-07-31 \
  --universe-csv /absolute/path/to/universe.csv \
  --universe-id official-sh-sz-2026-07-31 \
  --universe-source 'SSE and SZSE official same-session exports' \
  --output-root /absolute/path/to/market-breadth \
  --batch-size 50 \
  --max-capture-seconds 60 \
  --acknowledge-undocumented-sina
```

示例日期、ID 和批次大小只展示命令形状。不能直接复用为当前市场事实，批次大小必须来自本次有界探测。

`--license-note` 可以显式覆盖默认说明。默认说明只允许本地研究，并明确尚未建立匿名新浪端点的授权与再分发权利。

## 输出结构

成功导入会生成不可变版本目录，并原子更新 `current` 符号链接：

```text
market-breadth/
├── packages/
│   └── 2026-07-31-<dataset-prefix>/
│       ├── manifest.json
│       ├── universe.csv
│       ├── quotes.csv
│       └── evidence/
│           ├── sina-quotes-batch-0001.txt
│           └── ...
└── current -> packages/2026-07-31-<dataset-prefix>
```

`manifest.json` 记录：

- `schema_version=market-breadth-package-v0.2`；
- `session_date_evidence=provider-row-date`；
- 抓取开始与完成时间；
- `quote_contract=sina-hq-undocumented-observed-v0.1`；
- 批次大小和请求数量；
- 每个原始响应文件的字节数与 SHA-256；
- universe/quotes 的字节数与 SHA-256；
- 数据源、universe 来源和本地使用说明。

加载器会重新校验全部文件并由后端复算市场温度。任何 evidence、CSV 或 manifest 被修改后，接口都会拒绝读取。

## 原子发布与失败行为

导入器先写入 `packages/.tmp-*`，只有完整包能被 `load_market_breadth_package()` 重读、且市场温度质量状态不是 `FAILED` 时，才移动为正式版本目录并替换 `current`。

下列情况返回结构化拒绝且不更新 `current`：

- 未显式确认未文档化来源；
- universe 为空、重复、字段错误或不属于目标交易日；
- 新浪 HTTP、编码或赋值结构错误；
- 返回额外、重复或遗漏证券；
- 任一有效行情的提供方日期与目标日期不一致；
- 价格非法；
- 抓取窗口超过 `--max-capture-seconds`；
- 分辨率未通过 `market-breadth-quality-v0.1`；
- 相同 dataset 版本目录已经存在；
- 写入后的包无法重新通过完整性校验。

网络重试只适用于连接错误、超时和 `5xx`，最多 2 次。`403`、`429`、字段畸形和日期错配立即失败，不做无界重试。

## 与运行应用的关系

成功导入后，`current` 只供离线加载器、测试或人工复查使用。`./start.sh` 和首页不会自动读取该路径；运行中的市场温度使用独立的远端观测模块。

原始响应哈希只能证明本地看到的字节没有在生成包后被修改，不能证明字段准确、接口稳定、服务等级或使用授权。

## 验证

```bash
cd backend
uv run ruff check .
uv run pytest -q

cd ../frontend
npm test
npm run build

cd ..
bash -n start.sh
git diff --check
```

真实全市场验收必须另行记录目标交易日、universe 来源、批次大小、请求数量、抓取窗口、覆盖率、缺失原因和最终 dataset ID。没有完成真实开市日验收时，只能报告本地合成/录制响应验证通过。
