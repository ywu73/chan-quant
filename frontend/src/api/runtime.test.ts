import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchRuntimeCapabilities } from "./runtime";


afterEach(() => vi.unstubAllGlobals());


describe("runtime capabilities API client", () => {
  it("loads the same-origin deployment capability contract", async () => {
    const payload = {
      data_mode: "synthetic",
      remote_network_enabled: false,
      force_refresh_enabled: false,
      research_preview: true,
      release_sha: "b0a6280",
    };
    const request = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", request);
    const controller = new AbortController();

    await expect(fetchRuntimeCapabilities(controller.signal)).resolves.toEqual(payload);
    expect(request).toHaveBeenCalledWith(
      "/api/v1/runtime-capabilities",
      { signal: controller.signal },
    );
  });


  it("fails closed when the runtime contract is unavailable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 503 })),
    );

    await expect(fetchRuntimeCapabilities()).rejects.toThrow(
      "运行能力合同不可用（HTTP 503）",
    );
  });
});
