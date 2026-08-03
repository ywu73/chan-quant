import { describe, expect, it } from "vitest";

import { formatApiErrorDetail } from "./errorDetail";


describe("API error detail", () => {
  it("preserves a plain backend message", () => {
    expect(formatApiErrorDetail("upstream unavailable")).toBe("upstream unavailable");
  });

  it("surfaces a structured fail-closed reason code", () => {
    expect(formatApiErrorDetail({
      code: "REMOTE_NETWORK_DISABLED",
      message: "remote market access is disabled",
    })).toBe("remote market access is disabled [REMOTE_NETWORK_DISABLED]");
  });

  it("ignores unknown error shapes", () => {
    expect(formatApiErrorDetail({ message: "missing code" })).toBe("");
  });
});
