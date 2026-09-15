import { useCallback, useState } from "react";
import { apiClient } from "../../api/client";
import { useSession } from "../../session/SessionContext";
import { newIdempotencyKey } from "../../api/idempotency";
import { Button } from "../../components/Button/Button";
import { Textarea } from "../../components/Textarea/Textarea";
import { Alert } from "../../components/Alert/Alert";
import type { ApiError } from "../../api/errors";
import type { DecisionAction, Finding } from "../../api/types";
import styles from "./DecisionForm.module.css";

const ACTIONS: { value: DecisionAction; label: string }[] = [
  { value: "accept", label: "接受" },
  { value: "reject", label: "拒绝" },
  { value: "re-review", label: "重新评审" },
];

interface Props { reviewId: string; finding: Finding; onDecided: (f: Finding) => void }

export function DecisionForm({ reviewId, finding, onDecided }: Props) {
  const { actor } = useSession();
  const [action, setAction] = useState<DecisionAction>("accept");
  const [comment, setComment] = useState("");
  const [key, setKey] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  const submit = useCallback(async () => {
    if (!actor || busy) return;
    const k = key ?? newIdempotencyKey();
    setBusy(true);
    setError(null);
    try {
      const updated = await apiClient.decideFinding(actor, reviewId, finding.finding_id, { action, comment: comment.trim() }, { idempotencyKey: k, retry: { retries: 2, baseDelayMs: 50 } });
      setKey(k);
      onDecided(updated);
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setBusy(false);
    }
  }, [actor, busy, key, action, comment, reviewId, finding.finding_id, onDecided]);

  const reset = () => { setKey(null); setAction("accept"); setComment(""); };

  return (
    <form
      className={styles.form}
      onSubmit={(e) => { e.preventDefault(); void submit(); }}
      aria-label={`对需求 ${finding.requirement_id} 做出决策`}
    >
      <div role="radiogroup" aria-label="决策">
        {ACTIONS.map((a) => (
          <label key={a.value}>
            <input type="radio" name="action" value={a.value} checked={action === a.value} onChange={() => setAction(a.value)} />
            {a.label}
          </label>
        ))}
      </div>
      <Textarea id={`cmt-${finding.finding_id}`} label="意见（可选）" value={comment} onChange={setComment} maxLength={2000} />
      {error ? <Alert severity="error" message={error.message} correlationId={error.correlationId} /> : null}
      <div className={styles.row}>
        <Button type="submit" disabled={busy} aria-busy={busy}>{busy ? "提交中" : "提交决策"}</Button>
        <Button type="button" onClick={reset} disabled={busy}>重置</Button>
      </div>
    </form>
  );
}
