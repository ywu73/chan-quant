import { describe, expect, it } from "vitest";

import { dateRangeForPreset, validateIndexDateRange } from "./indexPerformance";


describe("index performance date ranges", () => {
  const today = new Date(2026, 7, 2, 12, 0, 0);

  it.each([
    ["3M", { start: "2026-05-02", end: "2026-08-02" }],
    ["6M", { start: "2026-02-02", end: "2026-08-02" }],
    ["1Y", { start: "2025-08-02", end: "2026-08-02" }],
    ["YTD", { start: "2026-01-01", end: "2026-08-02" }],
  ] as const)("builds the %s range in local calendar time", (preset, expected) => {
    expect(dateRangeForPreset(preset, today)).toEqual(expected);
  });

  it("clamps month offsets instead of rolling into the next month", () => {
    expect(dateRangeForPreset("3M", new Date(2026, 4, 31, 12, 0, 0))).toEqual({
      start: "2026-02-28",
      end: "2026-05-31",
    });
  });
});


describe("index performance custom range validation", () => {
  it("requires both calendar boundaries", () => {
    expect(validateIndexDateRange("", "2026-08-02")).toBe(
      "自定义区间必须同时提供开始日期和结束日期",
    );
    expect(validateIndexDateRange("2026-01-01", "")).toBe(
      "自定义区间必须同时提供开始日期和结束日期",
    );
  });

  it("rejects reversed ranges and accepts an ordered range", () => {
    expect(validateIndexDateRange("2026-08-02", "2026-01-01")).toBe(
      "开始日期不能晚于结束日期",
    );
    expect(validateIndexDateRange("2026-01-01", "2026-08-02")).toBeNull();
  });
});
