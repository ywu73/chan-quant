import type { ComparisonQuoteState } from "../comparisonQuotePolling";
import { formatPercent, formatPrice, formatQuoteTime } from "../format";
import type { MarketInstrument } from "../homeMarket";
import { QUOTE_STATUS_DISPLAY } from "../quoteDisplay";
import type { ComparisonFailure, ComparisonSeries } from "../types/comparison";


interface IndexPerformanceCardProps {
  instrument: MarketInstrument;
  series: ComparisonSeries | null;
  failure: ComparisonFailure | null;
  quoteState: ComparisonQuoteState;
}


function formatSignedPercent(value: number): string {
  return `${value > 0 ? "+" : ""}${formatPercent(value, 2)}`;
}


function returnTone(value: number | null | undefined): string {
  if (value === null || value === undefined || value === 0) return "neutral";
  return value > 0 ? "up" : "down";
}


export function IndexPerformanceCard({
  instrument,
  series,
  failure,
  quoteState,
}: IndexPerformanceCardProps) {
  const quote = quoteState.quote;
  const precision = series?.instrument.price_precision ?? 2;
  const drawdownRange = series?.max_drawdown_peak_at && series.max_drawdown_trough_at
    ? `${series.max_drawdown_peak_at} → ${series.max_drawdown_trough_at}`
    : series ? "区间内未出现收盘价回撤" : "--";

  return (
    <article className={`index-performance-card index-performance-card--${instrument.color}`}>
      <header className="index-performance-card__heading">
        <div>
          <span className="index-performance-card__dot" aria-hidden="true" />
          <strong>{instrument.displayName}</strong>
          <small>（{instrument.symbol}）</small>
        </div>
        <span className="index-performance-card__type">指数</span>
      </header>

      <dl className="index-performance-card__facts">
        <div>
          <dt>起始价</dt>
          <dd>{series ? formatPrice(series.baseline_price, precision) : "--"}</dd>
        </div>
        <div>
          <dt>区间末收盘</dt>
          <dd>{series ? formatPrice(series.latest_close, precision) : "--"}</dd>
        </div>
        <div>
          <dt>当前行情</dt>
          <dd>{quote ? formatPrice(quote.last_price, precision) : "--"}</dd>
        </div>
        <div>
          <dt>当日涨跌</dt>
          <dd className={`index-performance-card__value--${returnTone(quote?.change_percent)}`}>
            {quote ? formatSignedPercent(quote.change_percent) : "--"}
          </dd>
        </div>
        <div>
          <dt>上一交易日</dt>
          <dd className={`index-performance-card__value--${returnTone(series?.previous_trading_day_return)}`}>
            {series?.previous_trading_day_return === null || !series
              ? "--"
              : formatSignedPercent(series.previous_trading_day_return)}
          </dd>
        </div>
        <div>
          <dt>累计收益</dt>
          <dd className={`index-performance-card__value--${returnTone(series?.cumulative_return)}`}>
            {series ? formatSignedPercent(series.cumulative_return) : "--"}
          </dd>
        </div>
        <div>
          <dt>最大回撤</dt>
          <dd className={`index-performance-card__value--${returnTone(series?.max_drawdown)}`}>
            {series ? formatPercent(series.max_drawdown, 2) : "--"}
          </dd>
        </div>
        <div>
          <dt>回撤区间</dt>
          <dd>{drawdownRange}</dd>
        </div>
      </dl>

      {failure && (
        <p className="index-performance-card__error">
          [{failure.code}] {failure.message}
        </p>
      )}
      {quoteState.status === "ERROR" && (
        <p className="index-performance-card__error">实时行情：{quoteState.error}</p>
      )}

      <footer className="index-performance-card__footer">
        <div>
          <span>历史日 K 与独立行情分开计算</span>
          {series && <small>{series.data_source} · {series.adjustment}</small>}
        </div>
        <div>
          {quote
            ? <span>{quote.is_stale ? "行情已过期" : QUOTE_STATUS_DISPLAY[quote.status].label}</span>
            : <span>{quoteState.status === "LOADING" ? "行情连接中" : "行情不可用"}</span>}
          {quote && <small>{formatQuoteTime(quote.quote_at)} · {quote.source}</small>}
        </div>
      </footer>

      {series?.warnings.map((warning) => (
        <p className="index-performance-card__warning" key={warning.code}>{warning.message}</p>
      ))}
    </article>
  );
}
