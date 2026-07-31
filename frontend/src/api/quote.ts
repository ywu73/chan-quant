import type { QuoteSnapshot } from "../types/quote";


export async function fetchQuote(symbol: string): Promise<QuoteSnapshot> {
  const response = await fetch(
    `/api/v1/instruments/${encodeURIComponent(symbol)}/quote`,
  );
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: unknown;
    } | null;
    const detail = typeof payload?.detail === "string" ? `：${payload.detail}` : "";
    throw new Error(`实时行情不可用（HTTP ${response.status}）${detail}`);
  }
  return response.json() as Promise<QuoteSnapshot>;
}
