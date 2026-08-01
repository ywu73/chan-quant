import type { QuoteStatus } from "./types/quote";


export const QUOTE_STATUS_DISPLAY: Record<QuoteStatus, { label: string; tone: string }> = {
  LIVE: { label: "实时", tone: "positive" },
  DELAYED: { label: "延迟", tone: "warning" },
  CLOSED: { label: "已收盘", tone: "neutral" },
};
