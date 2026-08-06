import type { MouseEvent } from "react";


const DATA_SOURCES = [
  {
    name: "交易所证券列表",
    source: "上交所 / 深交所官方公开来源",
    purpose: "建立 CN_A_SH_SZ_V1 市场范围、证券身份与市场温度分母",
    status: "本地研究 GO",
    tone: "official",
    boundary: "负责身份与范围，不提供完整行情；公开可访问也不等于已取得商业使用或再分发许可。",
  },
  {
    name: "新浪行情能力",
    source: "新浪财经未文档化 Web 端点",
    purpose: "日 K、独立 Quote、批量 Quote、证券搜索与市场温度价格输入",
    status: "仅本地研究",
    tone: "observed",
    boundary: "没有固定字段合同或 SLA，不得作为生产行情；任一能力的现场证据不能自动外推到其他能力。",
  },
  {
    name: "外部 CSV",
    source: "用户提供并声明来源",
    purpose: "单标的历史日 K 研究输入",
    status: "声明可审计",
    tone: "declared",
    boundary: "系统检查格式、日期与声明，但不会把用户声明提升为外部认证，也不会伪装成多标的数据源。",
  },
  {
    name: "可审计历史快照",
    source: "用户获授权的外部导出",
    purpose: "通过 manifest、bars.csv 与 SHA-256 固化可复现数据集",
    status: "完整性可校验",
    tone: "auditable",
    boundary: "哈希一致只证明文件身份与完整性；复权经济含义、策略有效性和外部授权仍需分别判断。",
  },
  {
    name: "合成演示数据",
    source: "项目内确定性生成",
    purpose: "本地演示、开发与自动化测试",
    status: "非真实行情",
    tone: "synthetic",
    boundary: "可以复现，但不能被解释为市场观察、回测结果、交易绩效或实盘证据。",
  },
] as const;


const API_CONTRACTS = [
  ["GET /api/v1/instruments/search", "按代码或名称查询可解析的证券身份"],
  ["GET /api/v1/instruments/{symbol}/dashboard", "读取单标的日线研究快照与解释证据"],
  ["GET /api/v1/instruments/{symbol}/quote", "读取单标的独立实时行情快照"],
  ["GET /api/v1/quotes", "读取 1–8 个标的的批量独立 Quote"],
  ["GET /api/v1/market-comparison", "由后端计算多标的共同窗口、收益与回撤"],
  ["GET /api/v1/market-breadth", "读取 CN_A_SH_SZ_V1 市场温度与质量状态"],
] as const;


function handleInternalNavigation(
  event: MouseEvent<HTMLAnchorElement>,
  navigate: () => void,
) {
  if (
    event.defaultPrevented
    || event.button !== 0
    || event.metaKey
    || event.ctrlKey
    || event.shiftKey
    || event.altKey
  ) {
    return;
  }
  event.preventDefault();
  navigate();
}


export function DataMethodologyPage({ onNavigateHome }: { onNavigateHome: () => void }) {
  return (
    <main className="methodology-shell">
      <section className="methodology-hero">
        <div>
          <p className="home-section__eyebrow">DATA &amp; METHODOLOGY</p>
          <h1>先说明数据能证明什么，再展示研究结论</h1>
          <p>
            Chan Quant 把证券身份、行情来源、后端计算与前端展示分开记录。
            可追溯不等于交易所级认证，文件完整也不等于策略有效。
          </p>
          <div className="methodology-hero__actions">
            <a
              href="/"
              onClick={(event) => handleInternalNavigation(event, onNavigateHome)}
            >
              返回市场概况
            </a>
            <span>Independent v0.1 · Research Preview</span>
          </div>
        </div>
        <aside className="methodology-hero__boundary" aria-label="研究边界">
          <span>当前边界</span>
          <strong>研究与审计工具</strong>
          <ul>
            <li>不连接券商或放置订单</li>
            <li>不提供交易级行情或 SLA</li>
            <li>不把草案规则包装成确认策略</li>
            <li>不构成投资建议</li>
          </ul>
        </aside>
      </section>

      <section className="methodology-section" aria-labelledby="data-flow-title">
        <div className="methodology-section__heading">
          <div>
            <p className="home-section__eyebrow">DATA LINEAGE</p>
            <h2 id="data-flow-title">一条结论经过哪些边界</h2>
          </div>
          <p>每一层只拥有自己能够确认的事实。</p>
        </div>
        <div className="methodology-flow" aria-label="数据处理流程">
          <article>
            <span>01</span>
            <strong>证券身份</strong>
            <small>市场、交易所、代码、币种与时区</small>
          </article>
          <i aria-hidden="true">→</i>
          <article>
            <span>02</span>
            <strong>来源适配</strong>
            <small>官方列表、远端行情、CSV 或快照</small>
          </article>
          <i aria-hidden="true">→</i>
          <article>
            <span>03</span>
            <strong>后端校验</strong>
            <small>日期、覆盖率、完整性与拒绝原因</small>
          </article>
          <i aria-hidden="true">→</i>
          <article>
            <span>04</span>
            <strong>研究计算</strong>
            <small>结构、指标、事件与版本化结论</small>
          </article>
          <i aria-hidden="true">→</i>
          <article>
            <span>05</span>
            <strong>前端呈现</strong>
            <small>格式、布局、图表与交互</small>
          </article>
        </div>
        <p className="methodology-flow__note">
          Python 后端拥有指标、结构状态、信号、事件研究和策略结论；前端不复算策略规则。
        </p>
      </section>

      <section className="methodology-section" aria-labelledby="source-registry-title">
        <div className="methodology-section__heading">
          <div>
            <p className="home-section__eyebrow">SOURCE REGISTRY</p>
            <h2 id="source-registry-title">当前数据模式与证据边界</h2>
          </div>
          <p>按能力登记，不对供应商作笼统背书。</p>
        </div>
        <div className="methodology-table-wrap">
          <table className="methodology-source-table">
            <thead>
              <tr>
                <th scope="col">数据模式</th>
                <th scope="col">来源</th>
                <th scope="col">当前用途</th>
                <th scope="col">状态</th>
                <th scope="col">已知边界</th>
              </tr>
            </thead>
            <tbody>
              {DATA_SOURCES.map((source) => (
                <tr key={source.name}>
                  <th scope="row">{source.name}</th>
                  <td data-label="来源">{source.source}</td>
                  <td data-label="当前用途">{source.purpose}</td>
                  <td data-label="状态">
                    <span className={`methodology-status methodology-status--${source.tone}`}>
                      {source.status}
                    </span>
                  </td>
                  <td data-label="已知边界">{source.boundary}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="methodology-source-note">
          远端主源失败后禁止静默切换供应商；当前公开可访问状态也不能自动外推为商业使用或再分发许可。
        </p>
      </section>

      <section className="methodology-section" aria-labelledby="time-correctness-title">
        <div className="methodology-section__heading">
          <div>
            <p className="home-section__eyebrow">TIME CORRECTNESS</p>
            <h2 id="time-correctness-title">结构出现，不等于当时已经可执行</h2>
          </div>
          <p>历史图表位置与当时可获得的信息必须分开。</p>
        </div>
        <div className="methodology-time-grid">
          <article>
            <span>01 · LOCATION</span>
            <code>structure_at</code>
            <strong>结构所在位置</strong>
            <p>用于把分型、笔或其他结构定位在历史图表上，不能单独作为当时已经知道的证据。</p>
          </article>
          <article>
            <span>02 · CONFIRMATION</span>
            <code>confirmed_at</code>
            <strong>规则确认时点</strong>
            <p>规则首次拥有足够信息确认结构的时间；后续数据不得静默改写已经确认的历史身份。</p>
          </article>
          <article>
            <span>03 · EXECUTION</span>
            <code>executable_at</code>
            <strong>最早执行时点</strong>
            <p>事件研究和假设执行可以使用的第一个时点，仍受下一根 K 线、成交与研究假设约束。</p>
          </article>
        </div>
      </section>

      <section className="methodology-principles" aria-labelledby="failure-semantics-title">
        <article className="methodology-principles__intro">
          <p className="home-section__eyebrow">FAILURE SEMANTICS</p>
          <h2 id="failure-semantics-title">系统不会替上游失败编造一个完整答案</h2>
          <p>
            质量状态、覆盖率、缺失值和逐项失败属于研究结果的一部分，而不是需要从界面隐藏的噪声。
          </p>
        </article>
        <div className="methodology-principles__grid">
          <article><strong>不把缺失替换为零</strong><span>缺失日和不可用标的保持为空或失败状态。</span></article>
          <article><strong>不回退成演示数字</strong><span>远端失败不会自动切换为未标记的合成行情。</span></article>
          <article><strong>允许部分成功</strong><span>单标的失败不会清空同批次其他成功结果。</span></article>
          <article><strong>覆盖不足不画完整分布</strong><span>市场温度不满足质量门槛时保留拒绝原因。</span></article>
          <article><strong>身份可解析不等于行情获准</strong><span>未授权市场的日 K 与 Quote 必须结构化失败关闭。</span></article>
          <article><strong>完整性不等于外部认证</strong><span>SHA-256 证明文件未变，不能证明复权和策略有效。</span></article>
        </div>
      </section>

      <section className="methodology-section" aria-labelledby="api-contract-title">
        <div className="methodology-section__heading">
          <div>
            <p className="home-section__eyebrow">DEVELOPER APPENDIX</p>
            <h2 id="api-contract-title">项目拥有的 API 合同</h2>
          </div>
          <p>上游未文档化参数不是 Chan Quant 的稳定产品合同。</p>
        </div>
        <details className="methodology-api-details">
          <summary>展开查看当前主要读取接口</summary>
          <dl>
            {API_CONTRACTS.map(([endpoint, description]) => (
              <div key={endpoint}>
                <dt><code>{endpoint}</code></dt>
                <dd>{description}</dd>
              </div>
            ))}
          </dl>
          <p>
            HTTP 失败、无效输入、数据不足和远端不可用使用显式状态返回；具体字段合同以仓库中的
            API schema、数据合同与自动化测试为准。
          </p>
        </details>
      </section>

      <footer className="methodology-footer">
        <span>Chan Quant · Independent v0.1</span>
        <span>可追溯是证据边界，不是收益或可靠性保证</span>
      </footer>
    </main>
  );
}
