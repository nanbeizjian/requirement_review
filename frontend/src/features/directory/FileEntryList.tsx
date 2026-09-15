import { Button } from "../../components/Button/Button";
import type { SubmissionItem } from "./useDirectorySubmission";
import styles from "./FileEntryList.module.css";

const LABEL: Record<SubmissionItem["status"], string> = {
  pending: "等待中",
  submitting: "提交中",
  submitted: "已提交",
  failed: "失败",
};

export function FileEntryList({ items, onRetry }: { items: readonly SubmissionItem[]; onRetry: (id: number) => void }) {
  return (
    <ul className={styles.list} aria-label="提交队列">
      {items.map((it) => (
        <li key={it.id} className={styles.row} role="status" aria-live="polite">
          <span className={styles.name}>{it.name}</span>
          <span className={styles.status}>{LABEL[it.status]}</span>
          {it.status === "failed" ? (
            <span className={styles.err}>
              {it.errorMessage}
              {it.correlationId ? ` (关联 ID ${it.correlationId})` : ""}
              <Button onClick={() => onRetry(it.id)} aria-label={`重试 ${it.name}`}>重试</Button>
            </span>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
