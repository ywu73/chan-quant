export type MarketBreadthStatus = "COMPLETE" | "PARTIAL" | "FAILED";

export interface MarketBreadthBin {
  id:
    | "lt_m7"
    | "m7_m5"
    | "m5_m3"
    | "m3_m2"
    | "m2_m1"
    | "m1_0"
    | "p0_p1"
    | "p1_p2"
    | "p2_p3"
    | "p3_p5"
    | "p5_p7"
    | "gt_p7";
  label: string;
  side: "DECLINE" | "ADVANCE";
  count: number;
}

export interface MarketBreadthIssue {
  code: string;
  severity: "INFO" | "WARNING" | "DANGER";
  message: string;
}

export interface MarketBreadthSnapshot {
  status: MarketBreadthStatus;
  market: "CN_A_SH_SZ_V1";
  mode: "EOD" | "OBSERVED";
  session_date: string;
  universe_id: string;
  universe_as_of: string;
  snapshot_at: string;
  received_at: string;
  source: string;
  dataset_id: string;
  quality_policy_version: string;
  calculation_policy_version: string;
  universe_total: number;
  covered: number;
  unavailable: number;
  explicitly_unavailable: number;
  coverage_ratio: number;
  resolution_ratio: number;
  advancers: number;
  decliners: number;
  unchanged: number;
  bins: MarketBreadthBin[];
  unavailable_reasons: Record<string, number>;
  issues: MarketBreadthIssue[];
}
