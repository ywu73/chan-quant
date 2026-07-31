import type { InstrumentSearchResponse } from "../types/instrument";


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
    const payload = (await response.json().catch(() => null)) as {
      detail?: unknown;
    } | null;
    const detail = typeof payload?.detail === "string" ? `：${payload.detail}` : "";
    throw new Error(`证券搜索不可用（HTTP ${response.status}）${detail}`);
  }
  return response.json() as Promise<InstrumentSearchResponse>;
}
