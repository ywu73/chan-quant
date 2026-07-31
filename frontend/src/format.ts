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

export function formatPrice(value: number): string {
  return new Intl.NumberFormat("zh-CN", {
    style: "currency",
    currency: "CNY",
    currencyDisplay: "narrowSymbol",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
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
