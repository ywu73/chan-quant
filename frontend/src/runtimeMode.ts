import type { RuntimeCapabilities } from "./types/runtime";


const SAFE_CAPABILITIES: RuntimeCapabilities = {
  data_mode: "unknown",
  remote_network_enabled: false,
  force_refresh_enabled: false,
  research_preview: true,
  release_sha: "unknown",
};


export function safeRuntimeCapabilities(
  capabilities: RuntimeCapabilities | null,
): RuntimeCapabilities {
  return capabilities ?? SAFE_CAPABILITIES;
}


export function remoteRequestsAllowed(
  capabilities: RuntimeCapabilities | null,
): boolean {
  return capabilities?.remote_network_enabled === true;
}
