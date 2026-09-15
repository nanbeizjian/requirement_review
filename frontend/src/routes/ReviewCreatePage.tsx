import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSession } from "../session/SessionContext";
import { useClient } from "../lib/useClient";
import ErrorBanner from "../components/ErrorBanner";
import { ApiError } from "../lib/errors";
import type { DataPolicy } from "../api/types";

export default function ReviewCreatePage() {
  const { session } = useSession();
  const client = useClient();
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [policy, setPolicy] = useState<DataPolicy>("local_only");
  const [error, setError] = useState<Error | null>(null);

  const canSubmit = !!session && (session.role === "admin" || session.role === "reviewer");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!session) return;
    setError(null);
    try {
      const result = await client.createReview(session, {
        project_id: session.projectId,
        text,
        data_policy: policy,
      });
      navigate(`/reviews/${result.review_id}`);
    } catch (err) {
      setError(err as ApiError);
    }
  };

  return (
    <section aria-labelledby="create-heading">
      <h1 id="create-heading">New review</h1>
      <ErrorBanner error={error} />
      {!canSubmit && <p>You need a reviewer or admin session to start a review.</p>}
      {canSubmit && (
        <form onSubmit={submit}>
          <label>
            Requirement (Markdown)
            <textarea
              rows={12}
              maxLength={100000}
              value={text}
              onChange={(e) => setText(e.target.value)}
              required
            />
          </label>
          <label>
            Data policy
            <select value={policy} onChange={(e) => setPolicy(e.target.value as DataPolicy)}>
              <option value="local_only">local_only</option>
              <option value="cloud_allowed">cloud_allowed</option>
              <option value="cloud_redacted">cloud_redacted</option>
            </select>
          </label>
          <button type="submit">Submit</button>
        </form>
      )}
    </section>
  );
}
