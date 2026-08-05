import { formatPercent } from "../format";
import { getMarketTone } from "../marketTone";
import type { PortfolioStudy } from "../types/dashboard";


function formatCurrency(value: number): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    maximumFractionDigits: 2,
  }).format(value);
}


export function PortfolioStudyPanel({ study }: { study: PortfolioStudy }) {
  const { policy, statistics } = study;
  const rejectedReasons = Object.entries(statistics.rejected_reasons);

  return (
    <section className="portfolio-study" aria-label="假设组合研究">
      <header className="portfolio-study__header">
        <div>
          <p className="eyebrow">HYPOTHETICAL PORTFOLIO STUDY</p>
          <h2>▦ 假设组合研究</h2>
        </div>
        <span>不代表可实现交易绩效</span>
      </header>

      <p className="portfolio-study__boundary">
        长仓、单标的、信号次日开盘的一日有效意图；后端显式处理持仓、资金、整手、佣金、
        印花税、滑点、零成交与固定涨跌停假设，不重试被拒订单。
      </p>

      <dl className="portfolio-study__stats">
        <div>
          <dt>期末权益</dt>
          <dd>{formatCurrency(statistics.ending_equity)}</dd>
          <small>初始 {formatCurrency(statistics.starting_cash)}</small>
        </div>
        <div>
          <dt>假设总收益</dt>
          <dd className={`market-value--${getMarketTone(statistics.total_return)}`}>
            {formatPercent(statistics.total_return, 2)}
          </dd>
          <small>最大回撤 {formatPercent(statistics.max_drawdown, 2)}</small>
        </div>
        <div>
          <dt>已平仓胜率</dt>
          <dd>{formatPercent(statistics.win_rate, 1)}</dd>
          <small>{statistics.winning_positions}/{statistics.closed_positions} 笔已平仓</small>
        </div>
        <div>
          <dt>总成本</dt>
          <dd>{formatCurrency(statistics.total_costs)}</dd>
          <small>另计滑点影响 {formatCurrency(statistics.slippage_cost)}</small>
        </div>
        <div>
          <dt>成交 / 拒绝</dt>
          <dd>{statistics.filled_orders} / {statistics.rejected_orders}</dd>
          <small>期末持仓 {statistics.open_position_quantity} 股</small>
        </div>
        <div>
          <dt>资金暴露</dt>
          <dd>{formatPercent(statistics.exposure_ratio, 1)}</dd>
          <small>换手 {statistics.turnover.toFixed(2)}× 初始资金</small>
        </div>
      </dl>

      <div className="portfolio-study__policy">
        <strong>执行假设 · {policy.version}</strong>
        <span>佣金 {policy.commission_bps} bps（最低 {formatCurrency(policy.minimum_commission)}）</span>
        <span>卖出税 {policy.sell_tax_bps} bps</span>
        <span>单边滑点 {policy.slippage_bps} bps</span>
        <span>{policy.lot_size} 股整手</span>
        <span>最多使用 {formatPercent(policy.max_position_fraction, 0)} 资金</span>
        <span>固定涨跌停 ±{formatPercent(policy.price_limit_ratio, 0)}</span>
      </div>

      {rejectedReasons.length > 0 && (
        <div className="portfolio-study__rejections">
          <strong>未成交原因</strong>
          {rejectedReasons.map(([reason, count]) => (
            <span key={reason}><code>{reason}</code> × {count}</span>
          ))}
        </div>
      )}

      <div className="portfolio-study__warnings">
        {study.warnings.map((warning) => (
          <p key={warning.code}><strong>{warning.code}</strong>：{warning.message}</p>
        ))}
      </div>
    </section>
  );
}
