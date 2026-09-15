import type { InputHTMLAttributes } from "react";
import styles from "./FormField.module.css";

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "value" | "onChange"> {
  id: string; label: string; value: string; onChange: (v: string) => void; error?: string;
}

export function FormField({ id, label, value, onChange, error, required, ...rest }: Props) {
  const errId = `${id}-err`;
  return (
    <div className={styles.row}>
      <label htmlFor={id}>{label}{required ? " *" : ""}</label>
      <input
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-invalid={error ? "true" : undefined}
        aria-describedby={error ? errId : undefined}
        required={required}
        {...rest}
      />
      {error ? <span id={errId} role="alert" className={styles.err}>{error}</span> : null}
    </div>
  );
}
