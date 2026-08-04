import { describe, expect, it } from "vitest";

import { getMarketTone } from "./marketTone";


describe("A-share market direction tones", () => {
  it("maps positive, negative, zero, and unavailable values explicitly", () => {
    expect(getMarketTone(0.01)).toBe("up");
    expect(getMarketTone(-0.01)).toBe("down");
    expect(getMarketTone(0)).toBe("neutral");
    expect(getMarketTone(null)).toBe("neutral");
    expect(getMarketTone(undefined)).toBe("neutral");
  });
});
