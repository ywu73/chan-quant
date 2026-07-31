export interface InstrumentIdentity {
  symbol: string;
  name: string;
  exchange: "SZ" | "SH" | null;
  asset_type: "ETF" | "UNKNOWN";
  price_precision: number;
}

export interface InstrumentSearchResponse {
  query: string;
  items: InstrumentIdentity[];
  source: "sina-undocumented-suggest";
  limit: number;
}
