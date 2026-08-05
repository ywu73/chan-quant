export function formatPercent(value: number, digits = 1): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "percent",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

export function formatDate(value: string): string {
  return value.slice(5);
}

export function formatPrice(
  value: number,
  digits = 2,
  currency: "CNY" | "HKD" | "USD" = "CNY",
): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency,
    currencyDisplay: "symbol",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

export function formatPriceValue(value: number | string, digits = 2): string {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue.toFixed(digits) : String(value);
}

export function formatVolume(value: number): string {
  if (value >= 100_000_000) {
    return `${(value / 100_000_000).toFixed(2)} 亿`;
  }
  if (value >= 10_000) {
    return `${(value / 10_000).toFixed(2)} 万`;
  }
  return new Intl.NumberFormat("zh-CN").format(value);
}

export function formatQuoteTime(value: string): string {
  return value.replace("T", " ").slice(0, 19);
}
