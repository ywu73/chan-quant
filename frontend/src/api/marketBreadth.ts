import type { MarketBreadthSnapshot } from "../types/marketBreadth";
import { formatApiErrorDetail } from "./errorDetail";


export async function fetchMarketBreadth(
  signal?: AbortSignal,
  refresh = false,
): Promise<MarketBreadthSnapshot> {
  const url = `/api/v1/market-breadth?market=CN_A_SH_SZ_V1${refresh ? "&refresh=true" : ""}`;
  const response = signal ? await fetch(url, { signal }) : await fetch(url);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: unknown;
    } | null;
    const detail = formatApiErrorDetail(payload?.detail);
    const suffix = detail ? `：${detail}` : "";
    throw new Error(`市场温度不可用（HTTP ${response.status}）${suffix}`);
  }
  return response.json() as Promise<MarketBreadthSnapshot>;
}
