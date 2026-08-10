import { describe, expect, it } from "vitest";

import { remoteRequestsAllowed, safeRuntimeCapabilities } from "./runtimeMode";


describe("deployment runtime mode", () => {
  it("blocks remote requests before capabilities are known", () => {
    expect(remoteRequestsAllowed(null)).toBe(false);
    expect(safeRuntimeCapabilities(null)).toMatchObject({
      remote_network_enabled: false,
      force_refresh_enabled: false,
    });
  });


  it("only enables remote requests from an explicit backend capability", () => {
    expect(remoteRequestsAllowed({
      data_mode: "sina",
      remote_network_enabled: true,
      force_refresh_enabled: false,
      research_preview: true,
      release_sha: "online",
    })).toBe(true);
    expect(remoteRequestsAllowed({
      data_mode: "synthetic",
      remote_network_enabled: false,
      force_refresh_enabled: false,
      research_preview: true,
      release_sha: "offline",
    })).toBe(false);
  });
});
