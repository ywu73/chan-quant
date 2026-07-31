import type { DashboardSnapshot } from "../types/dashboard";


interface DataQualityRejection {
  status: "REJECTED";
  code: string;
  message: string;
}


function isDataQualityRejection(value: unknown): value is DataQualityRejection {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const candidate = value as Partial<DataQualityRejection>;
  return candidate.status === "REJECTED"
    && typeof candidate.code === "string"
    && typeof candidate.message === "string";
}

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
    const detail = typeof payload?.detail === "string"
      ? `：${payload.detail}`
      : isDataQualityRejection(payload?.detail)
        ? `：数据快照已拒绝 [${payload.detail.code}] ${payload.detail.message}`
        : "";
    throw new Error(`读取策略快照失败（HTTP ${response.status}）${detail}`);
  }
  return response.json() as Promise<DashboardSnapshot>;
}
