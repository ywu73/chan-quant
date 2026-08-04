import { describe, expect, it } from "vitest";

import {
  getFractalColor,
  getSignalColor,
  getStrokeColor,
  getVolumeBarColor,
} from "./chartStyle";

describe("chart colors", () => {
  it("colors volume bars by the matching candle direction", () => {
    expect(getVolumeBarColor(10, 11)).toBe("rgba(231, 85, 77, 0.55)");
    expect(getVolumeBarColor(11, 10)).toBe("rgba(82, 191, 104, 0.55)");
    expect(getVolumeBarColor(10, 10)).toBe("#d0d8e4");
  });

  it("uses A-share red-up and green-down colors for chart structures", () => {
    expect(getStrokeColor("UP")).toBe("#e7554d");
    expect(getStrokeColor("DOWN")).toBe("#52bf68");
    expect(getFractalColor("BOTTOM")).toBe("#e7554d");
    expect(getFractalColor("TOP")).toBe("#52bf68");
    expect(getSignalColor("BUY")).toBe("#e7554d");
    expect(getSignalColor("SELL")).toBe("#52bf68");
  });
});
