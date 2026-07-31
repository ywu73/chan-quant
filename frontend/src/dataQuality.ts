import type { DataQualityReport } from "./types/dashboard";


export function formatDatasetId(value: string): string {
  return value.length <= 28 ? value : `${value.slice(0, 15)}…${value.slice(-8)}`;
}


export function formatAdjustment(value: DataQualityReport["adjustment"]): string {
  return {
    qfq: "前复权",
    hfq: "后复权",
    unadjusted: "不复权",
  }[value];
}


export function formatAdjustmentBasis(
  value: DataQualityReport["adjustment_basis"],
): string {
  return value === "provider-declared" ? "供应商声明" : "外部审计引用";
}


export function dataQualityStatusLabel(
  value: DataQualityReport["status"] | "REJECTED",
): string {
  return {
    READY: "可用于研究",
    WARNING: "有界警告",
    REJECTED: "已拒绝",
  }[value];
}
