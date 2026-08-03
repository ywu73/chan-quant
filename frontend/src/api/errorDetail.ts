interface StructuredApiError {
  code: string;
  message: string;
}


function isStructuredApiError(value: unknown): value is StructuredApiError {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<StructuredApiError>;
  return typeof candidate.code === "string" && typeof candidate.message === "string";
}


export function formatApiErrorDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (isStructuredApiError(detail)) return `${detail.message} [${detail.code}]`;
  return "";
}
