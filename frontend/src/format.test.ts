import { describe, expect, it } from "vitest";

import { formatDate, formatPercent } from "./format";

describe("display formatting", () => {
  it("formats decimal ratios as percentages", () => {
    expect(formatPercent(25 / 26, 1)).toBe("96.2%");
    expect(formatPercent(-0.2085, 2)).toBe("-20.85%");
  });

  it("formats ISO dates for compact signal lists", () => {
    expect(formatDate("2026-07-21")).toBe("07-21");
  });
});
