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
  currency: "CNY" | "HKD" | "USD";
  is_mock: boolean;
  data_from: string;
  data_to: string;
  baseline_at: string;
  baseline_price: number;
  latest_close: number;
  previous_trading_day_return: number | null;
  values: Array<number | null>;
  cumulative_return: number;
  max_drawdown: number;
  max_drawdown_peak_at: string | null;
  max_drawdown_trough_at: string | null;
  coverage_ratio: number;
  warnings: ComparisonWarning[];
}


export interface ComparisonAlignment {
  date_basis: "LOCAL_TRADING_DATE";
  timezone_mode: "PER_INSTRUMENT_IANA";
  session_scope: "REGULAR_SESSION_CLOSE";
  currency_mode: "NATIVE_NO_FX_CONVERSION";
  missing_date_policy: "NULL_NO_FORWARD_FILL";
  overlap_policy: "INTERSECTION_OF_COVERAGE_WINDOWS";
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
  alignment: ComparisonAlignment;
  warnings: ComparisonWarning[];
  series: ComparisonSeries[];
  failures: ComparisonFailure[];
}
