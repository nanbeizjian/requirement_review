import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiClient } from "../../api/client";
import { useSession } from "../../session/SessionContext";
import type { ApiError } from "../../api/errors";
import { ReviewStatusHeader } from "./ReviewStatusHeader";
import { FindingFilters } from "./FindingFilters";
import { FindingCard } from "./FindingCard";
import { FinalApprovalGate } from "./FinalApprovalGate";
import { Alert } from "../../components/Alert/Alert";
import { Spinner } from "../../components/Spinner/Spinner";
import { useReviewPolling } from "./useReviewPolling";
import type { Finding } from "../../api/types";
import styles from "./ReviewDetailPage.module.css";

export function ReviewDetailPage() {
  const { reviewId = "" } = useParams();
  const { actor } = useSession();
  const { data: review, error: pollErr, stale, retry } = useReviewPolling(reviewId);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const [severity, setSeverity] = useState<string>("all");

  const reload = useCallback(async () => {
    if (!actor || !reviewId) return;
    try {
      const f = await apiClient.getFindings(actor, reviewId);
      setFindings(f);
    } catch (e) {
      setError(e as ApiError);
    }
  }, [actor, reviewId]);

  useEffect(() => { void reload(); }, [reload]);

  const filtered = useMemo(() => severity === "all" ? findings : findings.filter((f) => f.severity === severity), [findings, severity]);
  const pending = findings.filter((f) => f.decision === null || f.decision.action === "re-review").length;

  if (!review) return <Spinner label="加载评审" />;
  if (error || pollErr) return <Alert severity="error" message={(error ?? pollErr)!.message} correlationId={(error ?? pollErr)!.correlationId} />;

  return (
    <section className={styles.page}>
      <ReviewStatusHeader review={review} stale={stale} onRetry={retry} />
      {stale ? <Alert severity="warn" message="状态查询停滞，请重试。" /> : null}
      <FindingFilters severity={severity} onSeverityChange={setSeverity} />
      <p className={styles.pending}>剩余 {pending} 条待审核</p>
      <ol className={styles.cards}>
        {filtered.map((f) => (
          <li key={f.finding_id}>
            <FindingCard finding={f} onDecided={(updated) => setFindings((prev) => prev.map((x) => (x.finding_id === updated.finding_id ? updated : x)))} />
          </li>
        ))}
      </ol>
      <FinalApprovalGate review={review} findings={findings} />
      <p><Link to={`/reviews/${reviewId}/report`}>查看最终报告 →</Link></p>
    </section>
  );
}
