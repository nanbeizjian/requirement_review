import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useSession } from "../session/SessionContext";
import { useClient } from "../lib/useClient";
import ErrorBanner from "../components/ErrorBanner";
import { ApiError } from "../lib/errors";

export default function ReportPage() {
  const { reviewId = "" } = useParams();
  const { session } = useSession();
  const client = useClient();
  const [report, setReport] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!session) return;
    let active = true;
    setError(null);
    client
      .getReport(session, reviewId)
      .then((r) => {
        if (active) setReport(r);
      })
      .catch((err) => {
        if (active) setError(err as ApiError);
      });
    return () => {
      active = false;
      };
  }, [reviewId, session, client]);

  return (
    <section aria-labelledby="report-heading">
      <h1 id="report-heading">Report</h1>
      <ErrorBanner error={error} />
      {!session && <p>Set a session to read the report.</p>}
      {report && <pre className="report">{report}</pre>}
    </section>
  );
}
