import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient } from "../../api/client";
import { useSession } from "../../session/SessionContext";
import { useReviewsRefresher } from "./ReviewsRefreshContext";
import type { ApiError } from "../../api/errors";
import { ReviewListTable } from "./ReviewListTable";
import { DirectoryPicker } from "../directory/DirectoryPicker";
import { Alert } from "../../components/Alert/Alert";
import { Spinner } from "../../components/Spinner/Spinner";
import type { ReviewSummary } from "../../api/types";
import styles from "./ProjectReviewListPage.module.css";

export function ProjectReviewListPage() {
  const { actor } = useSession();
  const { refreshCounter } = useReviewsRefresher();
  const [reviews, setReviews] = useState<ReviewSummary[] | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  // inflightRef 标记一次进行中的 listReviews；needsRefetchRef 标记「完成
  // 后还需要再拉一次」。这样多次连续刷新只会触发最多一次额外请求。
  const inflightRef = useRef(false);
  const needsRefetchRef = useRef(false);

  const loadReviews = useCallback(async () => {
    if (inflightRef.current) {
      needsRefetchRef.current = true;
      return;
    }
    const a = actor;
    if (!a) return;
    inflightRef.current = true;
    try {
      const list = await apiClient.listReviews(a);
      // 仅在成功时清空旧错误；保留已有 rows（即使 setReviews 重新写入相同的列表）
      setReviews(list);
      setError(null);
    } catch (e) {
      if ((e as DOMException).name !== "AbortError") {
        setError(e as ApiError);
      }
    } finally {
      inflightRef.current = false;
      if (needsRefetchRef.current) {
        needsRefetchRef.current = false;
        void loadReviews();
      }
    }
  }, [actor]);

  useEffect(() => {
    if (!actor) return;
    const ac = new AbortController();
    // 主动走 loadReviews 复用合并逻辑；aborted 由调用方层处理。
    void loadReviews();
    return () => ac.abort();
  }, [actor, refreshCounter, loadReviews]);

  return (
    <section className={styles.page}>
      <DirectoryPicker />
      <h2>项目评审</h2>
      {error ? <Alert severity="error" message={error.message} correlationId={error.correlationId} /> : null}
      {reviews === null ? <Spinner label="加载中" /> : <ReviewListTable reviews={reviews} />}
    </section>
  );
}
