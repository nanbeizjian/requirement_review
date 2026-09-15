import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiClient } from "../../api/client";
import { useSession } from "../../session/SessionContext";
import type { ApiError } from "../../api/errors";
import { MarkdownView } from "./MarkdownView";
import { Alert } from "../../components/Alert/Alert";
import { Spinner } from "../../components/Spinner/Spinner";
import styles from "./ReportPage.module.css";

export function ReportPage() {
  const { reviewId = "" } = useParams();
  const { actor } = useSession();
  const [text, setText] = useState<string | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    if (!actor) return;
    const ac = new AbortController();
    apiClient.getReport(actor, reviewId).then(setText).catch((e) => {
      setError(e as ApiError);
    });
    return () => ac.abort();
  }, [actor, reviewId]);

  if (error) return <Alert severity="error" message={error.message} correlationId={error.correlationId} />;
  if (text === null) return <Spinner label="加载报告" />;
  return (
    <section aria-labelledby="report-h" className={styles.page}>
      <h2 id="report-h">最终报告</h2>
      <div role="region" aria-label="报告内容"><MarkdownView markdown={text} /></div>
    </section>
  );
}
