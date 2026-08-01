import type { ComparisonQuoteState } from "../comparisonQuotePolling";
import { formatPercent, formatPrice, formatQuoteTime } from "../format";
import { QUOTE_STATUS_DISPLAY } from "../quoteDisplay";
import type { ComparisonSeries } from "../types/comparison";

interface ComparisonMetricCardProps {
  series: ComparisonSeries;
  quoteState: ComparisonQuoteState;
}


export function ComparisonMetricCard({ series, quoteState }: ComparisonMetricCardProps) {
  const precision = series.instrument.price_precision;
  const quote = quoteState.quote;

  return (
    <article className="comparison-metric-card">
      <header>
        <div>
          <strong>{series.instrument.name}</strong>
          <span>{series.instrument.symbol}</span>
        </div>
        <small>{series.adjustment}</small>
      </header>

      <dl>
        <div><dt>起始价</dt><dd>{formatPrice(series.baseline_price, precision)}</dd></div>
        <div><dt>区间末收盘</dt><dd>{formatPrice(series.latest_close, precision)}</dd></div>
        <div><dt>累计收益</dt><dd>{formatPercent(series.cumulative_return, 2)}</dd></div>
        <div><dt>最大回撤</dt><dd>{formatPercent(series.max_drawdown, 2)}</dd></div>
        <div>
          <dt>上一交易日</dt>
          <dd>{series.previous_trading_day_return === null
            ? "--"
            : formatPercent(series.previous_trading_day_return, 2)}</dd>
        </div>
        <div><dt>有效覆盖</dt><dd>{formatPercent(series.coverage_ratio, 1)}</dd></div>
      </dl>

      <section className="comparison-metric-card__quote" aria-label="独立行情快照">
        <div className="comparison-metric-card__quote-heading">
          <strong>独立行情快照</strong>
          {quote && (
            <span className={quote.is_stale ? "is-stale" : ""}>
              {quote.is_stale ? "已过期" : QUOTE_STATUS_DISPLAY[quote.status].label}
            </span>
          )}
        </div>
        {quoteState.status === "LOADING" && <p>正在读取最新行情…</p>}
        {quoteState.status === "ERROR" && (
          <p className="comparison-metric-card__quote-error">{quoteState.error}</p>
        )}
        {quote && (
          <>
            <dl>
              <div><dt>最新价</dt><dd>{formatPrice(quote.last_price, precision)}</dd></div>
              <div><dt>当日涨跌</dt><dd>{formatPercent(quote.change_percent, 2)}</dd></div>
            </dl>
            <p>行情时间 {formatQuoteTime(quote.quote_at)}</p>
            <p>接收时间 {formatQuoteTime(quote.received_at)} · {quote.source}</p>
          </>
        )}
        <p>盘中价不参与历史比较指标计算</p>
      </section>

      <p>基准日期：{series.baseline_at}</p>
      <p>
        回撤区间：{series.max_drawdown_peak_at && series.max_drawdown_trough_at
          ? `${series.max_drawdown_peak_at} → ${series.max_drawdown_trough_at}`
          : "区间内未出现收盘价回撤"}
      </p>
      <p>历史来源：{series.data_source} · 币种：{series.currency}</p>
      {series.warnings.map((warning) => (
        <p className="comparison-metrics__warning" key={warning.code}>
          {warning.message}
        </p>
      ))}
    </article>
  );
}
