export type MarketTone = "up" | "down" | "neutral";
export type MarketDirection = "UP" | "DOWN" | "NEUTRAL";


export function getMarketTone(value: number | null | undefined): MarketTone {
  if (value === null || value === undefined || !Number.isFinite(value) || value === 0) {
    return "neutral";
  }
  return value > 0 ? "up" : "down";
}


export function getDirectionTone(
  direction: MarketDirection | null | undefined,
): MarketTone {
  if (direction === "UP") return "up";
  if (direction === "DOWN") return "down";
  return "neutral";
}
