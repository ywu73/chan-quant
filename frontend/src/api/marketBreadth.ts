import type { MarketBreadthSnapshot } from "../types/marketBreadth";


export async function fetchMarketBreadth(signal?: AbortSignal): Promise<MarketBreadthSnapshot> {
  const url = "/api/v1/market-breadth?market=CN_A_SH_SZ_V1";
  const response = signal ? await fetch(url, { signal }) : await fetch(url);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: unknown;
    } | null;
    const detail = payload?.detail;
    let suffix = "";
    if (typeof detail === "string") {
      suffix = `：${detail}`;
    } else if (detail && typeof detail === "object") {
      const rejection = detail as { code?: unknown; message?: unknown };
      const message = typeof rejection.message === "string" ? rejection.message : "";
      const code = typeof rejection.code === "string" ? rejection.code : "";
      suffix = message ? `：${message}${code ? ` [${code}]` : ""}` : "";
    }
    throw new Error(`市场温度不可用（HTTP ${response.status}）${suffix}`);
  }
  return response.json() as Promise<MarketBreadthSnapshot>;
}
