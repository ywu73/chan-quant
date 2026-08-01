import type { QuoteSnapshot } from "../types/quote";


export async function fetchQuote(
  symbol: string,
  signal?: AbortSignal,
): Promise<QuoteSnapshot> {
  const url = `/api/v1/instruments/${encodeURIComponent(symbol)}/quote`;
  const response = signal ? await fetch(url, { signal }) : await fetch(url);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: unknown;
    } | null;
    const detail = typeof payload?.detail === "string" ? `：${payload.detail}` : "";
    throw new Error(`实时行情不可用（HTTP ${response.status}）${detail}`);
  }
  return response.json() as Promise<QuoteSnapshot>;
}
