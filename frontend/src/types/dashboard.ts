export type Tone = "neutral" | "warning" | "danger" | "info" | "positive";

export interface Instrument {
  symbol: string;
  name: string;
  timeframe: string;
  as_of: string;
  last_price: number;
  currency: string;
  data_updated_at: string;
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
  tone: "blue" | "red" | "orange" | "purple" | "green" | "neutral";
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

export interface ChartBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  buy_line: number;
  sell_line: number;
  ma57: number;
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
    executable_at: string;
  };
  reasons: string[];
}

export interface DashboardSnapshot {
  is_mock: boolean;
  instrument: Instrument;
  status_chips: StatusChip[];
  metrics: MetricCardData[];
  recommendation: Recommendation;
  signal_performance: SignalPerformance;
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
