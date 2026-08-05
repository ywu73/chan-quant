export type Tone = "neutral" | "warning" | "danger" | "info" | "positive" | "bullish" | "bearish";

export interface Instrument {
  symbol: string;
  name: string;
  exchange: "SZ" | "SH" | null;
  asset_type: "ETF" | "UNKNOWN";
  price_precision: number;
  timeframe: string;
  as_of: string;
  last_price: number;
  currency: string;
  data_updated_at: string;
  data_source: string;
  adjustment: string;
}

export interface DataQualityIssue {
  code: string;
  severity: "INFO" | "WARNING" | "DANGER";
  message: string;
}

export interface DataQualityReport {
  status: "READY" | "WARNING";
  integrity: "MATCH";
  dataset_id: string;
  schema_version: "market-snapshot-v0.1";
  provider: string;
  adjustment: "qfq" | "hfq" | "unadjusted";
  adjustment_basis: "provider-declared" | "externally-audited";
  timeframe: "1d";
  timezone: "Asia/Shanghai";
  fetched_at: string;
  data_from: string;
  data_to: string;
  bar_count: number;
  bars_sha256: string;
  license_note: string;
  audit_reference: string | null;
  issues: DataQualityIssue[];
}

export interface StatusChip {
  label: string;
  tone: Tone;
}

export interface MetricCardData {
  key: string;
  label: string;
  value: string;
  detail: string;
  tone: "blue" | "red" | "orange" | "purple" | "green" | "neutral" | "bullish" | "bearish";
  value_direction: "UP" | "DOWN" | "NEUTRAL" | null;
  detail_direction: "UP" | "DOWN" | "NEUTRAL" | null;
}

export interface Recommendation {
  action: "WATCH" | "CANDIDATE_BUY" | "HOLD" | "CANDIDATE_EXIT";
  title: string;
  summary: string;
  filter_reasons: Array<{ code: string; message: string }>;
  evidence_lines: string[];
  warnings: Array<{ type: string; severity: string; message: string }>;
}

export interface SignalHorizon {
  bars: number;
  eligible: number;
  successes: number;
  success_rate: number;
  mean_forward_return: number;
}

export interface SidePerformance {
  side: "BUY" | "SELL";
  total_signals: number;
  horizons: SignalHorizon[];
  recent_signal_dates: string[];
}

export interface SignalPerformance {
  lookback_years: number;
  headline_total: number;
  excluded_total: number;
  excluded_reasons: Record<string, number>;
  buy: SidePerformance;
  sell: SidePerformance;
}

export interface PortfolioPolicy {
  version: string;
  initial_cash: number;
  commission_bps: number;
  minimum_commission: number;
  sell_tax_bps: number;
  slippage_bps: number;
  lot_size: number;
  max_position_fraction: number;
  price_limit_ratio: number;
  price_limit_decimals: number;
}

export interface PortfolioDecision {
  signal_id: string;
  side: "BUY" | "SELL";
  status: "FILLED" | "REJECTED" | "NOT_EXECUTABLE";
  reason_code: string;
  timing: {
    structure_at: string;
    confirmed_at: string;
    executable_at: string | null;
  };
  execution_price: number | null;
  quantity: number;
  notional: number;
  commission: number;
  transaction_tax: number;
  slippage_cost: number;
  cash_after: number;
  position_after: number;
}

export interface PortfolioMarketConstraint {
  date: string;
  trading_status: "OPEN" | "SUSPENDED";
  source: string;
  upper_limit: number | null;
  lower_limit: number | null;
}

export interface PortfolioEquityPoint {
  date: string;
  cash: number;
  position_quantity: number;
  close: number;
  equity: number;
}

export interface PortfolioStatistics {
  starting_cash: number;
  ending_equity: number;
  total_return: number;
  max_drawdown: number;
  filled_orders: number;
  rejected_orders: number;
  rejected_reasons: Record<string, number>;
  closed_positions: number;
  winning_positions: number;
  win_rate: number;
  total_costs: number;
  slippage_cost: number;
  turnover: number;
  exposure_ratio: number;
  open_position_quantity: number;
  realized_pnl: number;
  unrealized_pnl: number;
}

export interface PortfolioStudy {
  methodology_status: "HYPOTHETICAL_RESEARCH_ASSUMPTIONS";
  policy: PortfolioPolicy;
  market_constraints: PortfolioMarketConstraint[];
  statistics: PortfolioStatistics;
  decisions: PortfolioDecision[];
  equity_curve: PortfolioEquityPoint[];
  warnings: Array<{ code: string; message: string }>;
}

export interface ChartBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  buy_line: number | null;
  sell_line: number | null;
  ma57: number | null;
}

export interface FractalMarker {
  date: string;
  price: number;
  kind: "TOP" | "BOTTOM";
  status: "CONFIRMED" | "TENTATIVE";
}

export interface Stroke {
  direction: "UP" | "DOWN";
  points: Array<{ date: string; price: number }>;
  status: "CONFIRMED" | "TENTATIVE";
}

export interface SignalMarker {
  id: string;
  date: string;
  price: number;
  side: "BUY" | "SELL";
  label: string;
  timing: {
    structure_at: string;
    confirmed_at: string;
    executable_at: string | null;
  };
  reasons: string[];
}

export interface DashboardSnapshot {
  is_mock: boolean;
  instrument: Instrument;
  data_quality: DataQualityReport | null;
  status_chips: StatusChip[];
  metrics: MetricCardData[];
  recommendation: Recommendation;
  signal_performance: SignalPerformance;
  portfolio_study: PortfolioStudy;
  chart: {
    bars: ChartBar[];
    fractals: FractalMarker[];
    strokes: Stroke[];
    signals: SignalMarker[];
  };
  strategy: {
    version: string;
    parameter_version: string;
    rule_status: "MOCK" | "DRAFT" | "VALIDATED";
  };
}
