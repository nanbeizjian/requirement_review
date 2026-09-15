import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useSession } from "../session/SessionContext";
import { useClient } from "../lib/useClient";
import ErrorBanner from "../components/ErrorBanner";
import { newIdempotencyKey } from "../api/client";
import { ApiError } from "../lib/errors";
import type { FindingAction, ReviewFinding } from "../api/types";

export default function FindingsPage() {
  const { reviewId = "" } = useParams();
  const { session } = useSession();
  const client = useClient();
  const [findings, setFindings] = useState<ReviewFinding[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const canDecide = !!session && (session.role === "admin" || session.role === "reviewer");

  const refresh = async () => {
    if (!session) return;
    try {
      const list = await client.getFindings(session, reviewId);
      setFindings(list);
    } catch (err) {
      setError(err as ApiError);
    }
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reviewId, session]);

  const decide = async (findingId: string, action: FindingAction) => {
    if (!session) return;
    setBusyId(findingId);
    setError(null);
    try {
      await client.decideFinding(
        session,
        reviewId,
        findingId,
        { action },
        newIdempotencyKey("finding")
      );
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section aria-labelledby="findings-heading">
      <h1 id="findings-heading">Findings</h1>
      <ErrorBanner error={error} />
      {!findings.length && <p>No findings recorded yet.</p>}
      <ul>
        {findings.map((f) => (
          <li key={`${f.requirement_id}-${f.dimension}`} className="card">
            <p>
              <strong>{f.dimension}</strong> · {f.severity} · req {f.requirement_id}
            </p>
            <p>{f.issue}</p>
            <p>
              <em>Impact:</em> {f.impact}
            </p>
            <p>
              <em>Recommendation:</em> {f.recommendation}
            </p>
            <details>
              <summary>Evidence ({f.evidence.length})</summary>
              <ul>
                {f.evidence.map((e, idx) => (
                  <li key={idx}>
                    <code>{e.source_type}</code> doc={e.document_id} v{e.version}{" "}
                    loc=<code>{e.locator}</code> — “{e.quote}”
                  </li>
                ))}
              </ul>
            </details>
            {canDecide && (
              <div>
                <button
                  type="button"
                  disabled={busyId === f.requirement_id}
                  onClick={() => decide(f.requirement_id, "accept")}
                >
                  Accept
                </button>
                <button
                  type="button"
                  disabled={busyId === f.requirement_id}
                  onClick={() => decide(f.requirement_id, "reject")}
                >
                  Reject
                </button>
                <button
                  type="button"
                  disabled={busyId === f.requirement_id}
                  onClick={() => decide(f.requirement_id, "re-review")}
                >
                  Re-review
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
