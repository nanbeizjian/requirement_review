import { StatusBadge } from "../../components/StatusBadge/StatusBadge";
import { Button } from "../../components/Button/Button";
import { formatDateTime } from "../../lib/formatDate";
import type { ReviewDetail } from "../../api/types";
import styles from "./ReviewStatusHeader.module.css";

export function ReviewStatusHeader({ review, stale, onRetry }: { review: ReviewDetail; stale: boolean; onRetry: () => void }) {
  return (
    <header className={styles.header}>
      <h2>{review.source_name ?? review.review_id}</h2>
      <StatusBadge status={review.status} />
      <span className={styles.meta}>{formatDateTime(review.created_at)}</span>
      {stale ? <Button onClick={onRetry}>重试查询</Button> : null}
    </header>
  );
}
