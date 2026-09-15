import type { ApiErrorBody } from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly correlationId: string;
  constructor(status: number, code: string, message: string, correlationId: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.correlationId = correlationId;
  }
}

export async function parseApiError(res: Response): Promise<ApiError> {
  let body: Partial<ApiErrorBody> = {};
  try {
    body = (await res.json()) as Partial<ApiErrorBody>;
  } catch {
    /* not JSON */
  }
  return new ApiError(
    res.status,
    body.code ?? `http_${res.status}`,
    (body.message ?? res.statusText) || `request failed (${res.status})`,
    body.correlation_id ?? "",
  );
}
