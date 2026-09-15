import { Link } from "react-router-dom";
import { StatusBadge } from "../../components/StatusBadge/StatusBadge";
import { formatDateTime } from "../../lib/formatDate";
import type { ReviewSummary } from "../../api/types";
import styles from "./ReviewListTable.module.css";

export function ReviewListTable({ reviews }: { reviews: readonly ReviewSummary[] }) {
  if (reviews.length === 0) return <p className={styles.empty}>暂无评审任务。</p>;
  return (
    <table className={styles.table} aria-label="项目评审列表">
      <thead>
        <tr>
          <th>文档</th><th>状态</th><th>发现</th><th>待决</th><th>创建时间</th>
        </tr>
      </thead>
      <tbody>
        {reviews.map((r) => (
          <tr key={r.review_id}>
            <td><Link to={`/reviews/${r.review_id}`}>{r.source_name ?? r.review_id.slice(0, 8)}</Link></td>
            <td><StatusBadge status={r.status} /></td>
            <td>{r.finding_count}</td>
            <td>{r.pending_decision_count}</td>
            <td>{formatDateTime(r.created_at)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
