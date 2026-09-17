import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";

/**
 * 评审列表刷新信号通道。
 *
 * 触发侧（典型为 `useDirectorySubmission` 在一个批次内有任一文件
 * `submitted` 时）调用 `requestRefresh()`，消费侧（典型为
 * `ProjectReviewListPage`）订阅 `refreshCounter` 变化并重新拉取
 * `GET /api/v1/reviews`。
 *
 * 同 tick 内的连续调用（同步连发或同一微任务边界内）会被合并为一次递增，
 * 避免同步连续多次递增；不同批次（不同事件循环迭代）的调用各自递增一次。
 * 跨 await 的多次调用若发生在同一微任务边界内也会被合并；实际 `submit()`
 * 的实现只在批次结束且任一文件成功时调用一次，所以稳态只会触发一次递增。
 */
export interface ReviewsRefresher {
  refreshCounter: number;
  requestRefresh: () => void;
}

const Ctx = createContext<ReviewsRefresher | null>(null);

export function ReviewsRefreshProvider(props: { children: ReactNode }) {
  const [refreshCounter, setRefreshCounter] = useState(0);
  // 用 ref 暂存「同 tick 内是否还有未消费的递增请求」；下一次微任务边界才
  // 真正 setState，从而把同步连续多次调用合并为一次递增。
  const pendingTickRef = useRef(false);

  const requestRefresh = useCallback(() => {
    if (pendingTickRef.current) return;
    pendingTickRef.current = true;
    queueMicrotask(() => {
      pendingTickRef.current = false;
      setRefreshCounter((n) => n + 1);
    });
  }, []);

  const value = useMemo<ReviewsRefresher>(
    () => ({ refreshCounter, requestRefresh }),
    [refreshCounter, requestRefresh],
  );

  return <Ctx.Provider value={value}>{props.children}</Ctx.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useReviewsRefresher(): ReviewsRefresher {
  const v = useContext(Ctx);
  if (!v) {
    throw new Error("useReviewsRefresher must be used within ReviewsRefreshProvider");
  }
  return v;
}
