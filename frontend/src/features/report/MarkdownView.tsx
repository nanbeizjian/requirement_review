import { useMemo } from "react";
import styles from "./MarkdownView.module.css";

export function MarkdownView({ markdown }: { markdown: string }) {
  const escaped = useMemo(() => markdown.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]!)), [markdown]);
  return <pre className={styles.pre} aria-label="报告内容">{escaped}</pre>;
}
