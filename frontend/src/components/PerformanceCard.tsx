import { formatDate, formatPercent } from "../format";
import type { SidePerformance } from "../types/dashboard";

export function PerformanceCard({ performance }: { performance: SidePerformance }) {
  const isBuy = performance.side === "BUY";
  return (
    <article className={`performance-card performance-card--${isBuy ? "buy" : "sell"}`}>
      <header className="performance-card__header">
        <strong>{isBuy ? "一买" : "一卖"}</strong>
        <span>{performance.total_signals} 次</span>
      </header>

      <div className="performance-card__rows">
        {performance.horizons.map((item) => (
          <div className="performance-row" key={item.bars}>
            <span className="performance-row__horizon">{item.bars}日</span>
            <strong>{formatPercent(item.success_rate, item.success_rate > 0.9 ? 1 : 1)}</strong>
            <span className="performance-row__count">
              {item.successes}/{item.eligible}
            </span>
            <span className="performance-row__return">
              {formatPercent(item.mean_forward_return, 2)}
            </span>
          </div>
        ))}
      </div>

      <p className="performance-card__recent">
        最近：{performance.recent_signal_dates.map(formatDate).join(" · ")}
      </p>
    </article>
  );
}
