# 版本化行业与主题板块 preset 数据合同研究

## 结论

截至 **2026-08-02（Asia/Shanghai）**，数据合同结论为 **GO，但必须扩展内置板块的来源元数据后再实现**。

可以新增以下 3 个固定版本 preset，每组严格包含官方指数在 **2026-07-31** 的前 8 大权重证券：

1. **中证白酒前八权重**，来源指数 `399997` 中证白酒指数；
2. **CS 创新药前八权重**，来源指数 `931152` 中证创新药产业指数；
3. **半导体材料设备前八权重**，来源指数 `931743` 中证半导体材料设备主题指数。

三组共 24 个成员均由中证指数官网的同日权重响应和同日成分文件交叉确认，并逐项通过当前应用的 `NNNNNN.SH/SZ` 身份解析：代码、交易所、名称、`asset_type=UNKNOWN` 和两位价格精度都可由现有后端身份适配器返回。每组正好 8 个不同标的，符合比较页 `2–8` 上限。

**不能直接复用当前 `BuiltInBoard` 合同完成实现。** 现有类型只允许 `identity_source="sina-undocumented-suggest"`，无法表达“成员选择来自哪个官方指数、哪一天、按什么规则、当时权重是多少”。若只增加 8 个代码而不保存这些来源字段，应判定 **NO-GO**。现有约束见 [`frontend/src/comparisonBoards.ts`](../frontend/src/comparisonBoards.ts#L5-L22) 和 [`docs/data-contract.md`](data-contract.md#L176-L184)。

## 范围与证据边界

参考图 `/Users/wuyi/Downloads/IMG_6309.PNG` 与 `IMG_6310.PNG` 只用于识别“高端白酒、创新药、半导体设备”等 UI 主题，不作为成员依据：

- 官方 `399997` 覆盖白酒生产相关证券，不能缩写成“高端白酒”；
- 官方 `931743` 同时覆盖半导体材料和设备，不能缩写成纯“半导体设备”；
- 官方 `931152` 是创新药产业指数，样本可能包含创新药研发服务与产业链公司，不能解释成只包含已有创新药产品的制药公司。

核心成员与权重只采用中证指数有限公司的一手详情页、官方 `top10new` 权重响应、官方成分 XLS 和官方 factsheet。没有使用博客、论坛、社交媒体或第三方行情封装。

## 建议的数据合同

每个内置行业/主题 preset 至少应固化以下字段：

| 字段 | 建议值或规则 |
|---|---|
| `id` | 稳定 ID，例如 `csi-399997-top8`；版本更新不更换 ID |
| `name` | 明确包含“前八权重”，不能冒充完整行业或完整指数 |
| `version` | `2026-07-31`，与权重和成分归属日一致 |
| `confirmed_at` | `2026-08-02`，表示本项目现场确认日，不替代来源日期 |
| `membership_source` | `csi-official-index` |
| `index_code/index_name` | 官方指数代码和全称 |
| `source_as_of` | `2026-07-31` |
| `selection_rule` | `TOP_8_BY_OFFICIAL_PRECISE_WEIGHT` |
| `source_urls` | 官方详情页、`top10new`、同日成分 XLS 和 factsheet |
| `source_hashes` | 本次抓取的原始响应/文件 SHA-256，用于发现可变 URL 内容漂移 |
| `instruments` | 8 个完整 `BoardInstrument` 身份；另保留选择时的 `rank/weight/precise_weight` 审计证据 |

选择算法应固定为：

1. 要求官方响应 `success=true`、`code="200"`；
2. 要求 `data.updateDate` 与每一行 `tradeDate` 都等于 preset `source_as_of`；
3. 要求 `rowNum` 为连续的官方排名，并验证 `preciseWeight` 为有限正数且非递增；
4. 取官方排名前 8，不以四舍五入后的两位权重自行处理并列；
5. 根据官方 `marketNameCn` 映射交易所：上海证券交易所为 `.SH`，深圳证券交易所为 `.SZ`，未知市场直接失败；
6. 要求 8 个代码均为六位数字、互不重复，并存在于同一 `source_as_of` 的官方成分 XLS；
7. 任何日期不一致、字段缺失、未知交易所、重复、少于 8 项、无效权重或排序矛盾都应 fail closed，不使用旧成员静默补位。

官网 `top10new` 位于中证官方域名并被官网详情页使用，但没有公开 API 版本或 SLA。它适合作为**构建期/研究期的一手输入并固化成静态 preset**，不应成为浏览器运行时依赖。官方 URL 会原位更新，因此 `source_as_of`、抓取日和内容 SHA-256 必须同时保留。

## 候选一：中证白酒前八权重

- 指数代码与全称：`399997`，**中证白酒指数**；
- 官方定义：选取涉及白酒生产业务相关上市公司证券；
- factsheet 样本数：17，调样频率每半年，factsheet 日期 `2026-06-30`；
- 本 preset 权重与成分归属日：`2026-07-31`；
- 前 8 展示权重合计：**82.47%**。该比例只描述选择时的指数权重覆盖，不是本应用生成的组合权重。

| 排名 | 规范代码 | 身份名称 | 官方展示权重 | 官方 `preciseWeight` |
|---:|---|---|---:|---:|
| 1 | `600809.SH` | 山西汾酒 | 15.43% | 15.428831090540676 |
| 2 | `000568.SZ` | 泸州老窖 | 15.38% | 15.38236913472435 |
| 3 | `600519.SH` | 贵州茅台 | 15.30% | 15.29708689472685 |
| 4 | `000858.SZ` | 五粮液 | 13.95% | 13.954126614443497 |
| 5 | `002304.SZ` | 洋河股份 | 8.00% | 8.004741385532334 |
| 6 | `603369.SH` | 今世缘 | 6.65% | 6.6482397629260195 |
| 7 | `000596.SZ` | 古井贡酒 | 4.81% | 4.805405517638467 |
| 8 | `000799.SZ` | 酒鬼酒 | 2.95% | 2.9475329560757344 |

官方来源：

- [指数详情页](https://www.csindex.com.cn/#/indices/family/detail?indexCode=399997)
- [2026-07-31 十大权重响应](https://www.csindex.com.cn/csindex-home/index/weight/top10new/399997)，现场 SHA-256 `c8d1d32d1dfef27aa40d5a0f6d897a3365eda65d0060953b8600d06600cc6eae`
- [2026-07-31 成分 XLS](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/399997cons.xls)，现场 SHA-256 `e3a0af78260d22b3c8a123a01b3b7c587fcc0843a8af69e97866a81f1d64d5e5`
- [2026-06-30 factsheet](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/399997factsheet.pdf)，现场 SHA-256 `84f286a91fc71d55fb591ef9e9cb666eb91217319e231184bdd50d990bc15bf1`；用于指数定义、样本数和调样频率，不用于本 preset 的 7 月权重排序

官方资料名称为“五 粮 液”，当前应用身份适配器返回“五粮液”；代码和交易所一致。preset 的 `BoardInstrument.name` 应使用当前应用已核验身份名称，同时在来源审计中保留官方原始名称，避免把显示规范化误当成成员变化。

## 候选二：CS 创新药前八权重

- 指数代码与全称：`931152`，**中证创新药产业指数**；
- 官方定义：从主营业务涉及创新药研发的上市公司证券中选取不超过 50 只代表性证券；
- factsheet 样本数：50，调样频率每半年，factsheet 日期 `2026-06-30`；
- 本 preset 权重与成分归属日：`2026-07-31`；
- 前 8 展示权重合计：**41.66%**。

| 排名 | 规范代码 | 身份名称 | 官方展示权重 | 官方 `preciseWeight` |
|---:|---|---|---:|---:|
| 1 | `603259.SH` | 药明康德 | 11.24% | 11.241136772544513 |
| 2 | `600276.SH` | 恒瑞医药 | 9.89% | 9.891465119037061 |
| 3 | `002422.SZ` | 科伦药业 | 4.82% | 4.820611784114802 |
| 4 | `300759.SZ` | 康龙化成 | 3.79% | 3.792452008251634 |
| 5 | `002821.SZ` | 凯莱英 | 3.04% | 3.039827265679091 |
| 6 | `688578.SH` | 艾力斯 | 2.99% | 2.9920744852411514 |
| 7 | `688235.SH` | 百济神州 | 2.95% | 2.947324374166006 |
| 8 | `600196.SH` | 复星医药 | 2.94% | 2.942594961143083 |

官方来源：

- [指数详情页](https://www.csindex.com.cn/#/indices/family/detail?indexCode=931152)
- [2026-07-31 十大权重响应](https://www.csindex.com.cn/csindex-home/index/weight/top10new/931152)，现场 SHA-256 `bb4a359abbb9c18a393792d854f474553aaca3a8f78afb97113f9ed72496dd61`
- [2026-07-31 成分 XLS](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/931152cons.xls)，现场 SHA-256 `8830b56ee5b1397c522b53101a5e207ace4b5e070d6a5531420d2bb043b0478f`
- [2026-06-30 factsheet](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/931152factsheet.pdf)，现场 SHA-256 `cd00f1b524e288ac3e74fa8eac1e81f4e639755401bc36d597ac84c42f72e5f6`；仅用于指数定义、样本数和调样频率

## 候选三：半导体材料设备前八权重

- 指数代码与全称：`931743`，**中证半导体材料设备主题指数**；
- 官方定义：选取 40 只业务涉及半导体材料和半导体设备等领域的上市公司证券；
- factsheet 样本数：40，调样频率每半年，factsheet 日期 `2026-06-30`；
- 本 preset 权重与成分归属日：`2026-07-31`；
- 前 8 展示权重合计：**65.08%**。

| 排名 | 规范代码 | 身份名称 | 官方展示权重 | 官方 `preciseWeight` |
|---:|---|---|---:|---:|
| 1 | `688012.SH` | 中微公司 | 16.28% | 16.282013156459556 |
| 2 | `002371.SZ` | 北方华创 | 15.27% | 15.266593013085771 |
| 3 | `688072.SH` | 拓荆科技 | 8.31% | 8.308981004312631 |
| 4 | `300604.SZ` | 长川科技 | 7.28% | 7.280784196392078 |
| 5 | `688120.SH` | 华海清科 | 6.42% | 6.422308289832428 |
| 6 | `688361.SH` | 中科飞测 | 5.36% | 5.3645061576800135 |
| 7 | `688200.SH` | 华峰测控 | 3.17% | 3.1709554187218467 |
| 8 | `688037.SH` | 芯源微 | 2.99% | 2.988252020019651 |

官方来源：

- [指数详情页](https://www.csindex.com.cn/#/indices/family/detail?indexCode=931743)
- [2026-07-31 十大权重响应](https://www.csindex.com.cn/csindex-home/index/weight/top10new/931743)，现场 SHA-256 `61b90eb34b4e37fa443984b928596b12fcb964a82aeccf3ccd8deeec63b37e53`
- [2026-07-31 成分 XLS](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/931743cons.xls)，现场 SHA-256 `cd68c61e0b6cba76640ae8f76d6db1dbb1005070821f54966783d899648901c2`
- [2026-06-30 factsheet](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/indices/detail/files/zh_CN/931743factsheet.pdf)，现场 SHA-256 `65e1e7929741ef82a99a7492d7c4773afeb3e16412c350d50918806625dac21a`；仅用于指数定义、样本数和调样频率

## 当前应用身份与数量验证

中证权重响应的 `securityCode` 与 `marketNameCn` 被转换为规范代码，而不是根据代码首位猜交易所。24 个最终成员全部满足：

- `^\d{6}\.(SH|SZ)$`；
- 官方权重响应与同日成分 XLS 的代码、名称和交易所一致；
- 仓库现有 `to_sina_symbol` 可以逐项转换为 `sh/szNNNNNN`；
- 2026-08-02 现场调用现有精确身份适配器，24 项全部返回相同规范代码和交易所、非空名称、`asset_type=UNKNOWN`、`price_precision=2`；
- 每个 preset 恰好 8 个不同代码，满足 [`COMPARISON_MAX_INSTRUMENTS=8`](../frontend/src/comparisonBoards.ts#L5-L7)；后端仍会独立执行 2–8 个不同代码校验，不信任前端 preset，见 [`docs/data-contract.md`](data-contract.md#L176-L184)。

新浪身份响应只用于验证这些官方成员能进入当前应用，不参与成员选择或权重排序；官方 CSI 来源仍是 membership 的唯一事实源。

## 产品与计算风险

1. **这是 8 只成分股的快捷选择，不是完整行业。** UI 名称和描述必须明确“前八权重”，并显示来源指数与 `source_as_of`。
2. **比较页不会计算指数或组合收益。** 现有页面逐标的展示日 K 归一化走势和指标；官方权重只用于选择成员，不应用来暗示页面曲线是官方指数、加权组合或可交易产品。
3. **版本不会自动更新。** 调样或权重变化必须生成新 `version/source_as_of`，重新执行同日权重、成分、身份和数量验证；不能在保留旧版本号时替换成员。
4. **来源 URL 可变。** 官网 JSON、成分文件和 factsheet 均可能原位更新；内容哈希、来源日期和抓取确认日共同构成本次证据边界。
5. **行业标签存在范围差异。** 必须使用官方指数全称描述 preset，不能用参考图更窄或更营销化的标签覆盖官方语义。
6. **数据源边界不变。** preset 只提供身份入口，不改变后端新浪日 K 的未文档化、未复权观察和失败隔离合同，也不把结果提升为投资建议或行业推荐。

## 复现摘要

本次以低频方式分别读取 3 个官方权重响应和 3 个官方成分文件；没有把完整响应或 XLS/PDF 写入 Git。关键验证可按以下顺序重做：

```text
GET https://www.csindex.com.cn/csindex-home/index/weight/top10new/{indexCode}
GET https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/cons/{indexCode}cons.xls

indexCode in 399997, 931152, 931743
```

factsheet 的两页均完成文本抽取和 PNG 视觉核对，确认指数定义、日期、样本数、调样频率以及 2026-06-30 的十大权重表。7 月 preset 的排序只采用同日 `top10new` 精确权重与官方排名，未把 6 月 factsheet 权重混入 7 月版本。

研究阶段没有修改业务代码、保存凭证、写入完整市场数据、运行浏览器验收或执行任何 Git 远端操作。
