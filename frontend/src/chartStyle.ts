const UP_VOLUME_COLOR = "rgba(231, 85, 77, 0.55)";
const DOWN_VOLUME_COLOR = "rgba(82, 191, 104, 0.55)";
const FLAT_VOLUME_COLOR = "#d0d8e4";

export function getVolumeBarColor(open: number, close: number): string {
  if (close > open) return UP_VOLUME_COLOR;
  if (close < open) return DOWN_VOLUME_COLOR;
  return FLAT_VOLUME_COLOR;
}
