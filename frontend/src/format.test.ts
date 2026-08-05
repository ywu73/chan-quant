import { describe, expect, it } from "vitest";

import {
  formatDate,
  formatPrice,
  formatPriceValue,
  formatQuoteTime,
  formatVolume,
} from "./format";
import { formatPercent } from "./format";

describe("display formatting", () => {
  it("formats decimal ratios as percentages", () => {
    expect(formatPercent(25 / 26, 1)).toBe("96.2%");
    expect(formatPercent(-0.2085, 2)).toBe("-20.85%");
  });

  it("formats ISO dates for compact signal lists", () => {
    expect(formatDate("2026-07-21")).toBe("07-21");
  });

  it("formats quote facts without changing their meaning", () => {
    expect(formatPrice(11.6)).toBe("¥11.60");
    expect(formatPrice(2.112, 3)).toBe("¥2.112");
    expect(formatPrice(200.5, 2, "USD")).toBe("US$200.50");
    expect(formatPrice(300.5, 2, "HKD")).toBe("HK$300.50");
    expect(formatPriceValue(11.6)).toBe("11.60");
    expect(formatPriceValue("2.112", 3)).toBe("2.112");
    expect(formatPriceValue("--", 3)).toBe("--");
    expect(formatVolume(63_210_000)).toBe("6321.00 万");
    expect(formatVolume(632_100_000)).toBe("6.32 亿");
    expect(formatQuoteTime("2026-07-31T14:35:06+08:00")).toBe(
      "2026-07-31 14:35:06",
    );
  });
});
