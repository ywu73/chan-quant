import type { MetricCardData } from "../types/dashboard";
import { getDirectionTone } from "../marketTone";

export function MetricCard({ metric }: { metric: MetricCardData }) {
  return (
    <article className={`metric-card metric-card--${metric.tone}`}>
      <p className="metric-card__label">{metric.label}</p>
      <p className={`metric-card__value${metric.value_direction ? ` market-value market-value--${getDirectionTone(metric.value_direction)}` : ""}`}>{metric.value}</p>
      {metric.detail && (
        <p className={`metric-card__detail${metric.detail_direction ? ` market-value market-value--${getDirectionTone(metric.detail_direction)}` : ""}`}>
          {metric.detail}
        </p>
      )}
    </article>
  );
}
