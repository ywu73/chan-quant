import type { MetricCardData } from "../types/dashboard";

export function MetricCard({ metric }: { metric: MetricCardData }) {
  return (
    <article className={`metric-card metric-card--${metric.tone}`}>
      <p className="metric-card__label">{metric.label}</p>
      <p className="metric-card__value">{metric.value}</p>
      {metric.detail && <p className="metric-card__detail">{metric.detail}</p>}
    </article>
  );
}
