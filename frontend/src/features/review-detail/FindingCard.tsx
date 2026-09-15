import { useSession } from "../../session/SessionContext";
import { DecisionForm } from "./DecisionForm";
import type { Finding } from "../../api/types";
import styles from "./FindingCard.module.css";

export function FindingCard({ finding, onDecided }: { finding: Finding; onDecided: (f: Finding) => void }) {
  const { actor } = useSession();
  const writable = actor?.role === "reviewer" || actor?.role === "admin";
  return (
    <article className={styles.card} aria-labelledby={`f-${finding.finding_id}`}>
      <header>
        <h3 id={`f-${finding.finding_id}`}>{finding.dimension} · {finding.severity}</h3>
        <span className={styles.requirement}>需求 {finding.requirement_id}</span>
      </header>
      <dl>
        <dt>问题</dt><dd>{finding.issue}</dd>
        <dt>影响</dt><dd>{finding.impact}</dd>
        <dt>建议</dt><dd>{finding.recommendation}</dd>
        <dt>置信度</dt><dd>{(finding.confidence * 100).toFixed(0)}%</dd>
        <dt>证据</dt>
        <dd>
          <ul>
            {finding.evidence.map((e, i) => (
              <li key={i}><code>{e.locator}</code> — {e.quote}</li>
            ))}
          </ul>
        </dd>
        <dt>当前决策</dt><dd>{finding.decision ? `${finding.decision.action}${finding.decision.comment ? ` — ${finding.decision.comment}` : ""}` : "无"}</dd>
      </dl>
      {writable ? <DecisionForm reviewId="" finding={finding} onDecided={onDecided} /> : null}
    </article>
  );
}
