import { Select } from "../../components/Select/Select";
import styles from "./FindingFilters.module.css";

const OPTIONS: { value: string; label: string }[] = [
  { value: "all", label: "全部" },
  { value: "critical", label: "严重" },
  { value: "high", label: "高" },
  { value: "medium", label: "中" },
  { value: "low", label: "低" },
];

export function FindingFilters({ severity, onSeverityChange }: { severity: string; onSeverityChange: (v: string) => void }) {
  return (
    <div className={styles.row}>
      <Select id="sev" label="严重程度" value={severity} onChange={onSeverityChange} options={OPTIONS} />
    </div>
  );
}
