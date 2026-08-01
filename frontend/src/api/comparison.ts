import type { MarketComparison } from "../types/comparison";


export interface ComparisonDateRange {
  start?: string;
  end?: string;
}


export async function fetchMarketComparison(
  symbols: string[],
  range: ComparisonDateRange = {},
  signal?: AbortSignal,
): Promise<MarketComparison> {
  const params = new URLSearchParams();
  symbols.forEach((symbol) => params.append("symbols", symbol));
  if (range.start) params.set("start", range.start);
  if (range.end) params.set("end", range.end);

  const response = await fetch(`/api/v1/market-comparison?${params.toString()}`, { signal });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: unknown;
    } | null;
    const detail = typeof payload?.detail === "string" ? `：${payload.detail}` : "";
    throw new Error(`读取走势对比失败（HTTP ${response.status}）${detail}`);
  }
  return response.json() as Promise<MarketComparison>;
}
