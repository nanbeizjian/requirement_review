import styles from "./Spinner.module.css";

export function Spinner({ label = "加载中" }: { label?: string }) {
  return <span role="status" aria-live="polite" className={styles.spinner}>{label}</span>;
}
