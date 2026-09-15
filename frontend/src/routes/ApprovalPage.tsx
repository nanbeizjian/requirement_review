import { useState } from "react";
import { useParams } from "react-router-dom";
import { useSession } from "../session/SessionContext";
import { useClient } from "../lib/useClient";
import ErrorBanner from "../components/ErrorBanner";
import { newIdempotencyKey } from "../api/client";
import { ApiError } from "../lib/errors";
import type { ApprovalAction } from "../api/types";

export default function ApprovalPage() {
  const { reviewId = "" } = useParams();
  const { session } = useSession();
  const client = useClient();
  const [comment, setComment] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const canApprove = !!session && (session.role === "admin" || session.role === "reviewer");

  const submit = async (action: ApprovalAction) => {
    if (!session) return;
    setError(null);
    try {
      const r = await client.approveReview(
        session,
        reviewId,
        { action, comment },
        newIdempotencyKey("approval")
      );
      setResult(`review ${r.review_id} → ${r.status}`);
    } catch (err) {
      setError(err as ApiError);
    }
  };

  return (
    <section aria-labelledby="approval-heading">
      <h1 id="approval-heading">Approval</h1>
      <ErrorBanner error={error} />
      {!canApprove && <p>You need a reviewer or admin session to approve a review.</p>}
      {canApprove && (
        <>
          <label>
            Comment
            <textarea
              rows={4}
              maxLength={2000}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
          </label>
          <div>
            <button type="button" onClick={() => submit("approve")}>Approve</button>
            <button type="button" onClick={() => submit("modify")}>Modify</button>
            <button type="button" onClick={() => submit("reject")}>Reject</button>
            <button type="button" onClick={() => submit("re-review")}>Re-review</button>
          </div>
          <p>
            Each click generates a fresh idempotency key, surfaced here for retry safety.
          </p>
        </>
      )}
      {result && <p role="status">{result}</p>}
    </section>
  );
}
