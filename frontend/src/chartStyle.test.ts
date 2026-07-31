import { describe, expect, it } from "vitest";

import { getVolumeBarColor } from "./chartStyle";

describe("chart colors", () => {
  it("colors volume bars by the matching candle direction", () => {
    expect(getVolumeBarColor(10, 11)).toBe("rgba(231, 85, 77, 0.55)");
    expect(getVolumeBarColor(11, 10)).toBe("rgba(82, 191, 104, 0.55)");
    expect(getVolumeBarColor(10, 10)).toBe("#d0d8e4");
  });
});
