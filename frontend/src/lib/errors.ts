import type { ApiErrorBody } from "../api/types";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly correlationId: string;
  readonly body: ApiErrorBody | null;

  constructor(status: number, body: ApiErrorBody | null, fallback: string) {
    super(body?.message ?? fallback);
    this.name = "ApiError";
    this.status = status;
    this.code = body?.code ?? "unknown_error";
    this.correlationId = body?.correlation_id ?? "";
    this.body = body;
  }
}

/**
 * Decode a non-2xx response into a stable ApiError using the root public-contract
 * error shape. Never expose stack traces or secrets to callers.
 */
export async function readError(response: Response): Promise<ApiError> {
  const text = await response.text();
  let parsed: ApiErrorBody | null = null;
  if (text) {
    try {
      parsed = JSON.parse(text) as ApiErrorBody;
    } catch {
      parsed = null;
    }
  }
  return new ApiError(response.status, parsed, response.statusText || "request failed");
}
