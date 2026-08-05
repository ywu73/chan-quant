import { cnMarketContext, type InstrumentIdentity } from "./types/instrument";


export interface ObservedInstrumentIdentity extends InstrumentIdentity {
  identity_source: "sina-undocumented-suggest";
  confirmed_at: string;
}

export const CN_BROAD_INDEX_CATALOG: ObservedInstrumentIdentity[] = [
  { symbol: "000001.SH", name: "上证指数", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2, ...cnMarketContext("SH"), identity_source: "sina-undocumented-suggest", confirmed_at: "2026-08-01" },
  { symbol: "399001.SZ", name: "深证成指", exchange: "SZ", asset_type: "UNKNOWN", price_precision: 2, ...cnMarketContext("SZ"), identity_source: "sina-undocumented-suggest", confirmed_at: "2026-08-01" },
  { symbol: "399006.SZ", name: "创业板指", exchange: "SZ", asset_type: "UNKNOWN", price_precision: 2, ...cnMarketContext("SZ"), identity_source: "sina-undocumented-suggest", confirmed_at: "2026-08-01" },
  { symbol: "000300.SH", name: "沪深300", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2, ...cnMarketContext("SH"), identity_source: "sina-undocumented-suggest", confirmed_at: "2026-08-01" },
  { symbol: "000905.SH", name: "中证500", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2, ...cnMarketContext("SH"), identity_source: "sina-undocumented-suggest", confirmed_at: "2026-08-01" },
  { symbol: "000852.SH", name: "中证1000", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2, ...cnMarketContext("SH"), identity_source: "sina-undocumented-suggest", confirmed_at: "2026-08-01" },
  { symbol: "000688.SH", name: "科创50", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2, ...cnMarketContext("SH"), identity_source: "sina-undocumented-suggest", confirmed_at: "2026-08-01" },
  { symbol: "000016.SH", name: "上证50", exchange: "SH", asset_type: "UNKNOWN", price_precision: 2, ...cnMarketContext("SH"), identity_source: "sina-undocumented-suggest", confirmed_at: "2026-08-01" },
];

export const CN_BROAD_INDEX_BY_SYMBOL = new Map(
  CN_BROAD_INDEX_CATALOG.map((instrument) => [instrument.symbol, instrument]),
);
