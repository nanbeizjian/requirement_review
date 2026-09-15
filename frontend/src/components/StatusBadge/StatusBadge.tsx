import type { ReviewStatus } from "../../api/types";
import styles from "./StatusBadge.module.css";

const LABELS: Record<ReviewStatus, string> = {
  PENDING: "等待中",
  PARSING: "解析中",
  RETRIEVING: "检索知识",
  REVIEWING: "评审中",
  CONSOLIDATING: "汇总中",
  WAITING_APPROVAL: "待人工确认",
  COMPLETED: "已完成",
  FAILED: "失败",
};

export function StatusBadge({ status }: { status: ReviewStatus }) {
  return <span className={[styles.badge, styles[status]].join(" ")} aria-label={`状态：${LABELS[status]}`}>{LABELS[status]}</span>;
}
