import { formatPercent, formatPrice, formatQuoteTime, formatVolume } from "../format";
import type { QuoteSnapshot, QuoteStatus } from "../types/quote";


const STATUS_DISPLAY: Record<QuoteStatus, { label: string; tone: string }> = {
  LIVE: { label: "实时", tone: "positive" },
  DELAYED: { label: "延迟", tone: "warning" },
  CLOSED: { label: "已收盘", tone: "neutral" },
};


interface QuotePanelProps {
  symbol: string;
  instrumentName: string;
  pricePrecision: number;
  strategyAsOf: string;
  quote: QuoteSnapshot | null;
  error: string | null;
}


export function QuotePanel({
  symbol,
  instrumentName,
  pricePrecision,
  strategyAsOf,
  quote,
  error,
}: QuotePanelProps) {
  const status = quote ? STATUS_DISPLAY[quote.status] : null;
  const changeTone = quote && quote.change < 0 ? "negative" : "positive";

  return (
    <section className="quote-panel" aria-label="独立实时行情">
      <div className="quote-panel__header">
        <div>
          <p className="quote-panel__eyebrow">独立快照 · 不参与策略计算</p>
          <h2>新浪实时行情 · {instrumentName || symbol}</h2>
        </div>
        <span
          className={`quote-status quote-status--${error ? "danger" : (status?.tone ?? "info")}`}
          aria-live="polite"
        >
          {error ? "不可用" : (status?.label ?? "连接中")}
        </span>
      </div>

      {quote && !error ? (
        <>
          <div className="quote-panel__content">
            <div className="quote-panel__price">
              <strong>{formatPrice(quote.last_price, pricePrecision)}</strong>
              <span className={`quote-change quote-change--${changeTone}`}>
                {quote.change >= 0 ? "+" : ""}{quote.change.toFixed(pricePrecision)} · {formatPercent(quote.change_percent, 2)}
              </span>
            </div>
            <dl className="quote-facts">
              <div><dt>今开</dt><dd>{formatPrice(quote.open, pricePrecision)}</dd></div>
              <div><dt>最高</dt><dd>{formatPrice(quote.high, pricePrecision)}</dd></div>
              <div><dt>最低</dt><dd>{formatPrice(quote.low, pricePrecision)}</dd></div>
              <div><dt>成交量</dt><dd>{formatVolume(quote.volume)}</dd></div>
            </dl>
          </div>
          <div className="quote-panel__meta">
            <span>行情时间 {formatQuoteTime(quote.quote_at)}</span>
            <span>接收时间 {formatQuoteTime(quote.received_at)}</span>
            <span>{quote.source}</span>
          </div>
        </>
      ) : (
        <p className={`quote-panel__state${error ? " quote-panel__state--error" : ""}`}>
          {error ?? "正在读取独立实时快照…"}
        </p>
      )}

      <p className="quote-panel__boundary">
        日线策略仍只使用截至 {strategyAsOf} 的已收盘 K 线；这里的盘中价不会改变指标、结构、信号或事件研究。
      </p>
    </section>
  );
}
