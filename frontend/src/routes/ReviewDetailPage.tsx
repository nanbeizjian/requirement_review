import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useSession } from "../session/SessionContext";
import { useClient } from "../lib/useClient";
import ErrorBanner from "../components/ErrorBanner";
import { ApiError } from "../lib/errors";
import type { ReviewSummary } from "../api/types";

export default function ReviewDetailPage() {
  const { reviewId = "" } = useParams();
  const { session } = useSession();
  const client = useClient();
  const [summary, setSummary] = useState<ReviewSummary | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!session) return;
    let active = true;
    setError(null);
    client
      .getReview(session, reviewId)
      .then((r) => {
        if (active) setSummary(r);
      })
      .catch((err) => {
        if (active) setError(err as ApiError);
      });
    return () => {
      active = false;
    };
  }, [session, reviewId, client]);

  return (
    <section aria-labelledby="detail-heading">
      <h1 id="detail-heading">Review {reviewId}</h1>
      <ErrorBanner error={error} />
      {!session && <p>Set a session to view this review.</p>}
      {summary && (
        <div className="card">
          <p>
            Status: <strong>{summary.status}</strong>
          </p>
          {summary.failed_dimensions.length > 0 && (
            <p>Failed dimensions: {summary.failed_dimensions.join(", ")}</p>
          )}
          <ul>
            <li><Link to={`/reviews/${reviewId}/findings`}>Findings</Link></li>
            <li><Link to={`/reviews/${reviewId}/approval`}>Approval</Link></li>
            <li><Link to={`/reviews/${reviewId}/report`}>Report</Link></li>
          </ul>
        </div>
      )}
    </section>
  );
}
