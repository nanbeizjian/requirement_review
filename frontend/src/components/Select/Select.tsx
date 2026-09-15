import styles from "./Select.module.css";

interface Option<V extends string> { value: V; label: string }

interface Props<V extends string> {
  id: string; label: string; value: V; onChange: (v: V) => void; options: readonly Option<V>[]; disabled?: boolean;
}

export function Select<V extends string>({ id, label, value, onChange, options, disabled }: Props<V>) {
  return (
    <div className={styles.row}>
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value as V)} disabled={disabled}>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}
