import type { ComparisonDateRange } from "./api/comparison";


export type IndexRangePreset = "3M" | "6M" | "1Y" | "YTD";

export const INDEX_RANGE_PRESETS: Array<{ value: IndexRangePreset; label: string }> = [
  { value: "3M", label: "近 3 个月" },
  { value: "6M", label: "近 6 个月" },
  { value: "1Y", label: "近 1 年" },
  { value: "YTD", label: "今年以来" },
];


function formatLocalDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}


function subtractCalendarMonths(date: Date, months: number): Date {
  const targetIndex = date.getFullYear() * 12 + date.getMonth() - months;
  const targetYear = Math.floor(targetIndex / 12);
  const targetMonth = ((targetIndex % 12) + 12) % 12;
  const lastTargetDay = new Date(targetYear, targetMonth + 1, 0).getDate();
  return new Date(targetYear, targetMonth, Math.min(date.getDate(), lastTargetDay));
}


export function dateRangeForPreset(
  preset: IndexRangePreset,
  today = new Date(),
): Required<ComparisonDateRange> {
  const end = formatLocalDate(today);
  if (preset === "YTD") {
    return { start: `${today.getFullYear()}-01-01`, end };
  }
  const months = preset === "3M" ? 3 : preset === "6M" ? 6 : 12;
  return { start: formatLocalDate(subtractCalendarMonths(today, months)), end };
}


export function validateIndexDateRange(start: string, end: string): string | null {
  if (!start || !end) {
    return "自定义区间必须同时提供开始日期和结束日期";
  }
  return start > end ? "开始日期不能晚于结束日期" : null;
}
