import type { Finding, ReviewDetail } from "../../api/types";
import { ApprovalForm } from "./ApprovalForm";
import { useSession } from "../../session/SessionContext";
import styles from "./FinalApprovalGate.module.css";

export function FinalApprovalGate({ review, findings }: { review: ReviewDetail; findings: readonly Finding[] }) {
  const { actor } = useSession();
  const writable = actor?.role === "reviewer" || actor?.role === "admin";
  const allResolved = findings.length === 0 || findings.every((f) => {
    const d = f.decision;
    return d !== null && d.action !== "re-review";
  });
  const enabled = allResolved && review.status !== "COMPLETED";
  return (
    <section aria-labelledby="gate-h" className={styles.gate}>
      <h3 id="gate-h">最终确认</h3>
      <p className={enabled ? styles.ok : styles.disabled}>
        {enabled ? "所有评审点已决定，可执行最终确认。" : "存在未决或重新评审的评审点。"}
      </p>
      {writable ? <ApprovalForm reviewId={review.review_id} disabled={!enabled} /> : null}
    </section>
  );
}
