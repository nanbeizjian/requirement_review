import type { TextareaHTMLAttributes } from "react";
import styles from "./Textarea.module.css";

interface Props extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "id" | "value" | "onChange"> {
  id: string; label: string; value: string; onChange: (v: string) => void; error?: string;
}

export function Textarea({ id, label, value, onChange, error, ...rest }: Props) {
  const errId = `${id}-err`;
  return (
    <div className={styles.row}>
      <label htmlFor={id}>{label}</label>
      <textarea id={id} value={value} onChange={(e) => onChange(e.target.value)} aria-invalid={error ? "true" : undefined} aria-describedby={error ? errId : undefined} {...rest} />
      {error ? <span id={errId} role="alert" className={styles.err}>{error}</span> : null}
    </div>
  );
}
