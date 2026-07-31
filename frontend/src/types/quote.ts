export type QuoteStatus = "LIVE" | "DELAYED" | "CLOSED";

export interface QuoteSnapshot {
  symbol: string;
  name: string;
  last_price: number;
  previous_close: number;
  change: number;
  change_percent: number;
  open: number;
  high: number;
  low: number;
  volume: number;
  quote_at: string;
  received_at: string;
  source: "sina-undocumented-quote";
  status: QuoteStatus;
  is_stale: boolean;
}
