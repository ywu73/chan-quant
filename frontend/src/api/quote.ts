import type { QuoteSnapshot } from "../types/quote";
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
