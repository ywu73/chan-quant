import type { DashboardSnapshot } from "../types/dashboard";

export async function fetchDashboard(symbol: string): Promise<DashboardSnapshot> {
  const response = await fetch(`/api/v1/instruments/${encodeURIComponent(symbol)}/dashboard`);
  if (!response.ok) {
    throw new Error(`读取策略快照失败（HTTP ${response.status}）`);
  }
  return response.json() as Promise<DashboardSnapshot>;
}
