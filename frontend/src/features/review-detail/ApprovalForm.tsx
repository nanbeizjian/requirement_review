import { useState } from "react";
import { apiClient } from "../../api/client";
import { useSession } from "../../session/SessionContext";
import { newIdempotencyKey } from "../../api/idempotency";
import { Button } from "../../components/Button/Button";
import { Textarea } from "../../components/Textarea/Textarea";
import { Alert } from "../../components/Alert/Alert";
import type { ApiError } from "../../api/errors";
import styles from "./ApprovalForm.module.css";

export function ApprovalForm({ reviewId, disabled }: { reviewId: string; disabled?: boolean }) {
  const { actor } = useSession();
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [done, setDone] = useState(false);

  async function submit() {
    if (!actor || busy) return;
    setBusy(true); setError(null);
    try {
      await apiClient.approve(actor, reviewId, { action: "approve", comment: comment.trim() }, { idempotencyKey: newIdempotencyKey() });
      setDone(true);
    } catch (e) { setError(e as ApiError); } finally { setBusy(false); }
  }

  return (
    <form className={styles.form} onSubmit={(e) => { e.preventDefault(); void submit(); }}>
      <Textarea id="apr-cmt" label="意见（可选）" value={comment} onChange={setComment} maxLength={2000} />
      {error ? <Alert severity="error" message={error.message} correlationId={error.correlationId} /> : null}
      <Button type="submit" disabled={disabled || busy} aria-busy={busy}>{done ? "已确认" : busy ? "提交中" : "最终确认"}</Button>
    </form>
  );
}
