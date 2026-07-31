import { describe, expect, it } from "vitest";

import {
  dataQualityStatusLabel,
  formatAdjustment,
  formatAdjustmentBasis,
  formatDatasetId,
} from "./dataQuality";


describe("data quality display", () => {
  it("translates backend audit enums without changing their meaning", () => {
    expect(dataQualityStatusLabel("READY")).toBe("可用于研究");
    expect(dataQualityStatusLabel("WARNING")).toBe("有界警告");
    expect(dataQualityStatusLabel("REJECTED")).toBe("已拒绝");
    expect(formatAdjustment("qfq")).toBe("前复权");
    expect(formatAdjustment("hfq")).toBe("后复权");
    expect(formatAdjustment("unadjusted")).toBe("不复权");
    expect(formatAdjustmentBasis("provider-declared")).toBe("供应商声明");
    expect(formatAdjustmentBasis("externally-audited")).toBe("外部审计引用");
  });

  it("keeps a recognizable prefix and suffix for long dataset ids", () => {
    const value = `sha256:${"a".repeat(64)}`;
    expect(formatDatasetId(value)).toBe(`sha256:${"a".repeat(8)}…${"a".repeat(8)}`);
    expect(formatDatasetId("short-id")).toBe("short-id");
  });
});
