import type { InstrumentIdentity } from "./instrument";


export interface ComparisonWarning {
  code: string;
  message: string;
}


export interface ComparisonFailure {
  symbol: string;
  code: string;
  message: string;
}


export interface ComparisonSeries {
  instrument: InstrumentIdentity;
  data_source: string;
  adjustment: string;
  currency: "CNY";
  is_mock: boolean;
  data_from: string;
  data_to: string;
  baseline_at: string;
  values: Array<number | null>;
  cumulative_return: number;
  max_drawdown: number;
  max_drawdown_peak_at: string | null;
  max_drawdown_trough_at: string | null;
  coverage_ratio: number;
  warnings: ComparisonWarning[];
}


export interface MarketComparison {
  status: "COMPLETE" | "PARTIAL" | "FAILED";
  requested: string[];
  succeeded: number;
  failed: number;
  requested_from: string | null;
  requested_to: string | null;
  common_from: string | null;
  common_to: string | null;
  dates: string[];
  series: ComparisonSeries[];
  failures: ComparisonFailure[];
}
