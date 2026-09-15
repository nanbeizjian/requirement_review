import styles from "./Alert.module.css";

interface Props {
  severity: "info" | "warn" | "error" | "success";
  message: string;
  correlationId?: string;
}

export function Alert({ severity, message, correlationId }: Props) {
  return (
    <div role="alert" className={[styles.alert, styles[severity]].join(" ")}>
      <span>{message}</span>
      {correlationId ? <span className={styles.cid}>关联 ID: {correlationId}</span> : null}
    </div>
  );
}
