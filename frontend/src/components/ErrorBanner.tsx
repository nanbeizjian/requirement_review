import type { ApiError } from "../lib/errors";

export default function ErrorBanner({ error }: { error: ApiError | Error | null }) {
  if (!error) return null;
  const correlation = (error as ApiError).correlationId;
  return (
    <div className="error-banner" role="alert">
      <strong>{(error as ApiError).code ?? "error"}:</strong> {error.message}
      {correlation && (
        <span style={{ marginLeft: 8, opacity: 0.7 }}>correlation={correlation}</span>
      )}
    </div>
  );
}
