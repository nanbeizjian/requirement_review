import { useEffect, useState } from "react";
import { apiClient } from "../../api/client";
import { useSession } from "../../session/SessionContext";
import type { ApiError } from "../../api/errors";
import { ReviewListTable } from "./ReviewListTable";
import { DirectoryPicker } from "../directory/DirectoryPicker";
import { Alert } from "../../components/Alert/Alert";
import { Spinner } from "../../components/Spinner/Spinner";
import type { ReviewSummary } from "../../api/types";
import styles from "./ProjectReviewListPage.module.css";

export function ProjectReviewListPage() {
  const { actor } = useSession();
  const [reviews, setReviews] = useState<ReviewSummary[] | null>(null);
  const [error, setError] = useState<ApiError | null>(null);

  useEffect(() => {
    if (!actor) return;
    const ac = new AbortController();
    apiClient.listReviews(actor, { signal: ac.signal }).then(setReviews).catch((e) => {
      if ((e as DOMException).name !== "AbortError") setError(e as ApiError);
    });
    return () => ac.abort();
  }, [actor]);

  return (
    <section className={styles.page}>
      <DirectoryPicker />
      <h2>项目评审</h2>
      {error ? <Alert severity="error" message={error.message} correlationId={error.correlationId} /> : null}
      {reviews === null ? <Spinner label="加载中" /> : <ReviewListTable reviews={reviews} />}
    </section>
  );
}
