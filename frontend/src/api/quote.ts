import type { QuoteBatch, QuoteSnapshot } from "../types/quote";
import { formatApiErrorDetail } from "./errorDetail";


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
    const detail = formatApiErrorDetail(payload?.detail);
    const suffix = detail ? `：${detail}` : "";
    throw new Error(`实时行情不可用（HTTP ${response.status}）${suffix}`);
  }
  return response.json() as Promise<QuoteSnapshot>;
}


export async function fetchQuotes(
  symbols: string[],
  signal?: AbortSignal,
): Promise<QuoteBatch> {
  const params = new URLSearchParams();
  symbols.forEach((symbol) => params.append("symbols", symbol));
  const url = `/api/v1/quotes?${params.toString()}`;
  const response = signal ? await fetch(url, { signal }) : await fetch(url);
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: unknown;
    } | null;
    const detail = formatApiErrorDetail(payload?.detail);
    const suffix = detail ? `：${detail}` : "";
    throw new Error(`批量实时行情不可用（HTTP ${response.status}）${suffix}`);
  }
  return response.json() as Promise<QuoteBatch>;
}
