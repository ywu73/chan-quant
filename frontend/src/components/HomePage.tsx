import { useCallback, useEffect, useState, type MouseEvent } from "react";

import { fetchMarketBreadth } from "../api/marketBreadth";
import { fetchQuote } from "../api/quote";
import { formatPercent, formatQuoteTime, formatVolume } from "../format";
import {
  HOME_MARKET_INSTRUMENTS,
  intradayRangePosition,
  loadMarketQuotes,
  type MarketQuoteResult,
} from "../homeMarket";
import { getMarketTone } from "../marketTone";
import { QUOTE_STATUS_DISPLAY } from "../quoteDisplay";
import type { MarketBreadthSnapshot } from "../types/marketBreadth";
import { MarketBreadthPanel } from "./MarketBreadthPanel";


const RESEARCH_MODULES = [
  {
    code: "01",
    title: "结构研究",
    detail: "严格三 K 分型、简化笔与原始结构证据",
    meta: "当前可用",
    tone: "blue",
  },
  {
    code: "02",
    title: "趋势状态",
    detail: "均线、Donchian 通道与多周期状态",
    meta: "当前可用",
    tone: "green",
  },
  {
    code: "03",
    title: "候选信号",
    detail: "规则版本、过滤原因与最早可执行时间",
    meta: "当前可用",
    tone: "orange",
  },
  {
    code: "04",
    title: "事件研究",
    detail: "5 / 10 / 20 个交易日的历史事件观察",
    meta: "当前可用",
    tone: "purple",
  },
  {
    code: "05",
    title: "走势对比",
    detail: "多标的归一化曲线、收益与回撤比较",
    meta: "当前可用",
    tone: "blue",
  },
  {
    code: "06",
    title: "市场温度",
    detail: "沪深 A 股远端涨跌分布、覆盖率与来源风险提示",
    meta: "当前可用",
    tone: "blue",
  },
] as const;


function formatIndexValue(value: number): string {
  return new Intl.NumberFormat("zh-CN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}


function MarketCard({ result }: { result: MarketQuoteResult }) {
  const { instrument, quote, error } = result;
  const direction = getMarketTone(quote?.change);
  const position = quote ? intradayRangePosition(quote) : 50;

  return (
    <article className={`home-market-card home-market-card--${instrument.color}`}>
      <div className="home-market-card__heading">
        <div>
          <span className="home-market-card__dot" aria-hidden="true" />
          <strong>{instrument.displayName}</strong>
          <small>{instrument.symbol}</small>
        </div>
        <span className={`home-market-card__status${error ? " home-market-card__status--error" : ""}`}>
          {error ? "不可用" : quote ? QUOTE_STATUS_DISPLAY[quote.status].label : "连接中"}
        </span>
      </div>

      {quote && !error ? (
        <>
          <div className="home-market-card__price">
            <strong>{formatIndexValue(quote.last_price)}</strong>
            <span className={`home-market-card__change home-market-card__change--${direction}`}>
              {quote.change >= 0 ? "+" : ""}{formatIndexValue(quote.change)}
              <b>{formatPercent(quote.change_percent, 2)}</b>
            </span>
          </div>
          <div className="home-market-card__range" aria-label="日内价格区间">
            <span className="home-market-card__range-fill" style={{ width: `${position}%` }} />
            <span className="home-market-card__range-point" style={{ left: `${position}%` }} />
          </div>
          <dl className="home-market-card__facts">
            <div><dt>今开</dt><dd>{formatIndexValue(quote.open)}</dd></div>
            <div><dt>最高</dt><dd>{formatIndexValue(quote.high)}</dd></div>
            <div><dt>最低</dt><dd>{formatIndexValue(quote.low)}</dd></div>
            <div><dt>成交量</dt><dd>{formatVolume(quote.volume)}</dd></div>
          </dl>
          <p className="home-market-card__time">行情时间 {formatQuoteTime(quote.quote_at)}</p>
        </>
      ) : (
        <div className={`home-market-card__empty${error ? " home-market-card__empty--error" : ""}`}>
          {error ? "单项行情读取失败，不影响其他指数快照。" : "正在读取独立实时快照…"}
        </div>
      )}
    </article>
  );
}


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


export function HomePage({
  onNavigateComparison,
  onNavigateMethodology,
  onNavigateResearch,
  remoteNetworkEnabled = true,
  forceRefreshEnabled = true,
}: {
  onNavigateComparison: () => void;
  onNavigateMethodology: () => void;
  onNavigateResearch: () => void;
  remoteNetworkEnabled?: boolean;
  forceRefreshEnabled?: boolean;
}) {
  const [marketResults, setMarketResults] = useState<MarketQuoteResult[]>(
    HOME_MARKET_INSTRUMENTS.map((instrument) => ({ instrument, quote: null, error: null })),
  );
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(true);
  const [breadthSnapshot, setBreadthSnapshot] = useState<MarketBreadthSnapshot | null>(null);
  const [breadthError, setBreadthError] = useState<string | null>(null);
  const [breadthRefreshVersion, setBreadthRefreshVersion] = useState(0);
  const [isBreadthLoading, setIsBreadthLoading] = useState(true);

  const refresh = useCallback(() => setRefreshVersion((value) => value + 1), []);
  const refreshBreadth = useCallback(
    () => setBreadthRefreshVersion((value) => value + 1),
    [],
  );

  useEffect(() => {
    if (!remoteNetworkEnabled) {
      setIsRefreshing(false);
      return undefined;
    }
    let active = true;
    const controller = new AbortController();
    setIsRefreshing(true);
    loadMarketQuotes(HOME_MARKET_INSTRUMENTS, fetchQuote, controller.signal)
      .then((results) => {
        if (active) {
          setMarketResults(results);
        }
      })
      .finally(() => {
        if (active) {
          setIsRefreshing(false);
        }
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [refreshVersion, remoteNetworkEnabled]);

  useEffect(() => {
    if (!remoteNetworkEnabled) {
      setIsBreadthLoading(false);
      setBreadthSnapshot(null);
      setBreadthError(null);
      return undefined;
    }
    let active = true;
    const controller = new AbortController();
    setIsBreadthLoading(true);
    setBreadthSnapshot(null);
    setBreadthError(null);
    fetchMarketBreadth(controller.signal, breadthRefreshVersion > 0)
      .then((snapshot) => {
        if (active) {
          setBreadthSnapshot(snapshot);
        }
      })
      .catch((error: unknown) => {
        if (active && !(error instanceof DOMException && error.name === "AbortError")) {
          setBreadthError(error instanceof Error ? error.message : "市场温度读取失败");
        }
      })
      .finally(() => {
        if (active) {
          setIsBreadthLoading(false);
        }
      });
    return () => {
      active = false;
      controller.abort();
    };
  }, [breadthRefreshVersion, remoteNetworkEnabled]);

  useEffect(() => {
    if (!remoteNetworkEnabled) return undefined;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") {
        refresh();
      }
    }, 60_000);
    return () => window.clearInterval(timer);
  }, [refresh, remoteNetworkEnabled]);

  const latestReceivedAt = marketResults
    .flatMap((result) => result.quote?.received_at ? [result.quote.received_at] : [])
    .sort()
    .at(-1);

  return (
    <main className="home-shell">
      <section className="home-hero">
        <div className="home-hero__content">
          <p className="home-kicker">AUDITABLE MARKET RESEARCH</p>
          <h1>把行情、结构与证据放在同一张研究桌上</h1>
          <p>
            从市场快照进入单标的结构研究。每一项结论都保留数据来源、规则版本、确认时间与原始证据。
          </p>
          <div className="home-hero__tags" aria-label="当前支持范围">
            <span>A 股</span><span>ETF</span><span>指数</span><span>日线研究</span>
          </div>
          <div className="home-hero__actions">
            <a
              className="home-hero__primary-action"
              href="/search"
              onClick={(event) => handleInternalNavigation(event, onNavigateResearch)}
            >
              开始研究
            </a>
            <a
              href="/methodology"
              onClick={(event) => handleInternalNavigation(event, onNavigateMethodology)}
            >
              查看数据与方法
            </a>
          </div>
        </div>
        <aside className="home-hero__boundary">
          <span className="home-hero__boundary-label">RESEARCH STATUS</span>
          <strong>Independent v0.1</strong>
          <p>草案规则 · 可复现 · 不使用未来数据</p>
          <small>仅供研究与审计，不连接券商，不构成交易建议。</small>
        </aside>
      </section>

      <section className="home-section" aria-labelledby="market-snapshot-title">
        <div className="home-section__heading">
          <div>
            <p className="home-section__eyebrow">MARKET SNAPSHOT</p>
            <h2 id="market-snapshot-title">主要指数快照</h2>
          </div>
          {remoteNetworkEnabled && (
            <div className="home-section__actions">
              <span>{latestReceivedAt ? `接收于 ${formatQuoteTime(latestReceivedAt)}` : "等待行情响应"}</span>
              <button type="button" onClick={refresh} disabled={isRefreshing}>
                {isRefreshing ? "刷新中" : "刷新"}
              </button>
            </div>
          )}
        </div>
        {remoteNetworkEnabled ? (
          <>
            <p className="home-section__note">
              新浪未文档化行情的独立快照；不进入日线策略链路，也不代表交易级行情服务。
            </p>
            <div className="home-market-grid">
              {marketResults.map((result) => (
                <MarketCard key={result.instrument.symbol} result={result} />
              ))}
            </div>
          </>
        ) : (
          <div className="home-offline-state" role="status">
            <strong>离线研究演示</strong>
            <span>远端指数快照已关闭；合成 Dashboard 与静态方法论仍可使用。</span>
          </div>
        )}
      </section>

      <MarketBreadthPanel
        snapshot={breadthSnapshot}
        isLoading={isBreadthLoading}
        error={breadthError}
        onRefresh={refreshBreadth}
        remoteNetworkEnabled={remoteNetworkEnabled}
        forceRefreshEnabled={forceRefreshEnabled}
      />

      <section className="home-section" aria-labelledby="research-modules-title">
        <div className="home-section__heading">
          <div>
            <p className="home-section__eyebrow">RESEARCH MODULES</p>
            <h2 id="research-modules-title">研究能力</h2>
          </div>
          <span className="home-section__summary">当前能力与后续边界分开呈现</span>
        </div>
        <div className="home-module-grid">
          {RESEARCH_MODULES.map((module) => (
            <article
              className={`home-module-card home-module-card--${module.tone}${module.code === "05" || module.code === "06" ? " home-module-card--available" : ""}`}
              key={module.code}
            >
              <div className="home-module-card__topline">
                <span>{module.code}</span>
                <small>{module.meta}</small>
              </div>
              <h3>{module.title}</h3>
              <p>{module.detail}</p>
              {module.code === "05" && (
                <button type="button" onClick={onNavigateComparison}>打开走势对比</button>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className="home-audit-grid">
        <article className="home-audit-card">
          <p className="home-section__eyebrow">AUDIT TIMELINE</p>
          <h2>结构发生，不等于当时可交易</h2>
          <div className="home-timeline" aria-label="结构审计时间线">
            <div><span>01</span><strong>structure_at</strong><small>结构所在位置</small></div>
            <i aria-hidden="true" />
            <div><span>02</span><strong>confirmed_at</strong><small>规则确认时点</small></div>
            <i aria-hidden="true" />
            <div><span>03</span><strong>executable_at</strong><small>最早执行时点</small></div>
          </div>
        </article>
        <article className="home-boundary-card">
          <span className="home-boundary-card__icon" aria-hidden="true">i</span>
          <div>
            <p className="home-section__eyebrow">DATA BOUNDARY</p>
            <h2>数据状态必须可见</h2>
            <p>合成行情、外部 CSV 和未文档化行情使用不同标识；缺失值和上游失败不会被静默替换为零或演示数字。</p>
            <a
              href="/methodology"
              onClick={(event) => handleInternalNavigation(event, onNavigateMethodology)}
            >
              查看数据谱系、计算口径与失败语义 →
            </a>
          </div>
        </article>
      </section>

      <footer className="home-footer">
        <span>Chan Quant · Independent v0.1 草案</span>
        <span className="home-footer__links">
          <a
            href="/methodology"
            onClick={(event) => handleInternalNavigation(event, onNavigateMethodology)}
          >
            数据与方法
          </a>
          <span aria-hidden="true">·</span>
          <span>研究与审计工具 · 不构成交易建议</span>
        </span>
      </footer>
    </main>
  );
}
