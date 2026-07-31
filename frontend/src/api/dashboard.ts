import type { DashboardSnapshot } from "../types/dashboard";

export async function fetchDashboard(
  symbol: string,
  signal?: AbortSignal,
): Promise<DashboardSnapshot> {
  const response = await fetch(
    `/api/v1/instruments/${encodeURIComponent(symbol)}/dashboard`,
    { signal },
  );
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      detail?: unknown;
    } | null;
    const detail = typeof payload?.detail === "string" ? `：${payload.detail}` : "";
    throw new Error(`读取策略快照失败（HTTP ${response.status}）${detail}`);
  }
  return response.json() as Promise<DashboardSnapshot>;
}
