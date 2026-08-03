import type { InstrumentIdentity, InstrumentSearchResponse } from "../types/instrument";
import { formatApiErrorDetail } from "./errorDetail";


async function instrumentFailure(response: Response): Promise<Error> {
  const payload = (await response.json().catch(() => null)) as {
    detail?: unknown;
  } | null;
  const detail = formatApiErrorDetail(payload?.detail);
  const suffix = detail ? `：${detail}` : "";
  return new Error(`证券搜索不可用（HTTP ${response.status}）${suffix}`);
}


export async function resolveInstrument(
  symbol: string,
  signal?: AbortSignal,
): Promise<InstrumentIdentity> {
  const canonical = symbol.trim().toUpperCase();
  const response = await fetch(
    `/api/v1/instruments/${encodeURIComponent(canonical)}`,
    { signal },
  );
  if (!response.ok) throw await instrumentFailure(response);
  return response.json() as Promise<InstrumentIdentity>;
}


export async function searchInstruments(
  query: string,
  signal?: AbortSignal,
  limit = 8,
): Promise<InstrumentSearchResponse> {
  const normalizedQuery = query.trim();
  const response = await fetch(
    `/api/v1/instruments/search?q=${encodeURIComponent(normalizedQuery)}&limit=${limit}`,
    { signal },
  );
  if (!response.ok) {
    throw await instrumentFailure(response);
  }
  return response.json() as Promise<InstrumentSearchResponse>;
}
