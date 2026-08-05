export interface InstrumentIdentity {
  symbol: string;
  name: string;
  exchange: "SZ" | "SH" | "HKEX" | "NASDAQ" | "NYSE" | "NYSE_ARCA" | "CBOE" | null;
  asset_type: "EQUITY" | "ETF" | "INDEX" | "UNKNOWN";
  price_precision: number;
  market: "CN" | "HK" | "US" | "GLOBAL" | "SYNTHETIC" | null;
  mic: "XSHE" | "XSHG" | "XHKG" | "XNAS" | "XNYS" | "ARCX" | "XCBO" | null;
  currency: "CNY" | "HKD" | "USD" | null;
  timezone: string | null;
  trading_calendar: "XSHE" | "XSHG" | "XHKG" | "XNAS" | "XNYS" | "ARCX" | "XCBO" | "DETERMINISTIC_DEMO" | null;
  provider_symbols: Record<string, string>;
}


export function cnMarketContext(exchange: "SZ" | "SH") {
  return {
    market: "CN" as const,
    mic: exchange === "SZ" ? "XSHE" as const : "XSHG" as const,
    currency: "CNY" as const,
    timezone: "Asia/Shanghai",
    trading_calendar: exchange === "SZ" ? "XSHE" as const : "XSHG" as const,
    provider_symbols: {},
  };
}

export interface InstrumentSearchResponse {
  query: string;
  items: InstrumentIdentity[];
  source: "sina-undocumented-suggest";
  limit: number;
}
