export const MARKET_UP_COLOR = "#e7554d";
export const MARKET_DOWN_COLOR = "#52bf68";

const UP_VOLUME_COLOR = "rgba(231, 85, 77, 0.55)";
const DOWN_VOLUME_COLOR = "rgba(82, 191, 104, 0.55)";
const FLAT_VOLUME_COLOR = "#d0d8e4";

export function getVolumeBarColor(open: number, close: number): string {
  if (close > open) return UP_VOLUME_COLOR;
  if (close < open) return DOWN_VOLUME_COLOR;
  return FLAT_VOLUME_COLOR;
}

export function getStrokeColor(direction: "UP" | "DOWN"): string {
  return direction === "UP" ? MARKET_UP_COLOR : MARKET_DOWN_COLOR;
}

export function getFractalColor(kind: "TOP" | "BOTTOM"): string {
  return kind === "BOTTOM" ? MARKET_UP_COLOR : MARKET_DOWN_COLOR;
}

export function getSignalColor(side: "BUY" | "SELL"): string {
  return side === "BUY" ? MARKET_UP_COLOR : MARKET_DOWN_COLOR;
}
