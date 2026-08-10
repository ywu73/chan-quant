import type { RuntimeCapabilities } from "../types/runtime";


export async function fetchRuntimeCapabilities(
  signal?: AbortSignal,
): Promise<RuntimeCapabilities> {
  const response = await fetch("/api/v1/runtime-capabilities", { signal });
  if (!response.ok) {
    throw new Error(`运行能力合同不可用（HTTP ${response.status}）`);
  }
  return response.json() as Promise<RuntimeCapabilities>;
}
