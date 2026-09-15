import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient, type Actor } from "../../api/client";
import { useSession } from "../../session/SessionContext";
import type { ApiError } from "../../api/errors";
import type { ReviewDetail } from "../../api/types";

export interface UseReviewPollingOptions {
  initialMs?: number;
  maxMs?: number;
  staleAfter?: number;
}

export interface UseReviewPollingResult {
  data: ReviewDetail | null;
  error: ApiError | null;
  stale: boolean;
  retry: () => void;
}

const DEFAULTS = { initialMs: 1000, maxMs: 5000, staleAfter: 5 };

export function useReviewPolling(reviewId: string | null, options: UseReviewPollingOptions = {}): UseReviewPollingResult {
  const { actor } = useSession();
  const { initialMs, maxMs, staleAfter } = { ...DEFAULTS, ...options };
  const [data, setData] = useState<ReviewDetail | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [stale, setStale] = useState(false);
  const [tick, setTick] = useState(0);
  const consecutiveErrors = useRef(0);
  const timer = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const retry = useCallback(() => {
    consecutiveErrors.current = 0;
    setStale(false);
    setError(null);
    setTick((n) => n + 1);
  }, []);

  useEffect(() => {
    if (!actor || !reviewId) return;
    let cancelled = false;
    let delay = initialMs;

    const schedule = (ms: number) => {
      if (cancelled) return;
      timer.current = window.setTimeout(tickOnce, ms);
    };

    const tickOnce = async () => {
      if (cancelled) return;
      abortRef.current = new AbortController();
      const a: Actor = actor;
      try {
        const res = await apiClient.getReview(a, reviewId, { signal: abortRef.current.signal });
        if (cancelled) return;
        consecutiveErrors.current = 0;
        setStale(false);
        setData(res);
        setError(null);
        if (res.status === "WAITING_APPROVAL" || res.status === "COMPLETED" || res.status === "FAILED") return;
        delay = Math.min(delay * 2, maxMs);
        schedule(delay);
      } catch (e) {
        if (cancelled) return;
        if ((e as DOMException).name === "AbortError") return;
        consecutiveErrors.current += 1;
        if (consecutiveErrors.current >= staleAfter) setStale(true);
        setError(e as ApiError);
        delay = Math.min(delay * 2, maxMs);
        schedule(delay);
      }
    };

    tickOnce();

    return () => {
      cancelled = true;
      if (timer.current !== null) window.clearTimeout(timer.current);
      abortRef.current?.abort();
    };
  }, [actor, reviewId, tick, initialMs, maxMs, staleAfter]);

  return { data, error, stale, retry };
}
