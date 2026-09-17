import { useCallback, useRef, useState } from "react";
import { apiClient, type Actor } from "../../api/client";
import { useSession } from "../../session/SessionContext";
import { useReviewsRefresher } from "../reviews/ReviewsRefreshContext";
import { basename } from "../../lib/paths";
import type { DataPolicy } from "../../api/types";

export interface SubmissionFile {
  name: string;
  text: string;
}

// 后端 ReviewCreate.data_policy 为必填字段，且服务层要求提交值与项目
// data_policy 完全一致（不一致返回 422）。前端 Session/Actor 未携带项目
// data_policy，后端亦无查询项目策略的接口，因此无法动态读取；此处使用与
// 后端 ProjectCreate 默认值一致的 cloud_allowed（默认上云策略），
// 默认路径创建的项目（未显式指定 data_policy）均为该值。
const DEFAULT_DATA_POLICY: DataPolicy = "cloud_allowed";

export type SubmissionStatus = "pending" | "submitting" | "submitted" | "failed";

export interface SubmissionItem {
  id: number;
  name: string;
  status: SubmissionStatus;
  reviewId?: string;
  errorMessage?: string;
  correlationId?: string;
  text: string;
}

export interface SubmissionSummary {
  total: number;
  pending: number;
  submitting: number;
  submitted: number;
  completed: number;
  failed: number;
}

export interface UseDirectorySubmissionOptions {
  concurrency?: number;
}

export interface UseDirectorySubmissionResult {
  items: SubmissionItem[];
  summary: SubmissionSummary;
  submit: (files: readonly SubmissionFile[]) => Promise<void>;
  retry: (id: number) => Promise<void>;
}

const DEFAULT_CONCURRENCY = 3;

export function useDirectorySubmission(options: UseDirectorySubmissionOptions = {}): UseDirectorySubmissionResult {
  const { actor } = useSession();
  const { requestRefresh } = useReviewsRefresher();
  const concurrency = options.concurrency ?? DEFAULT_CONCURRENCY;
  const [items, setItems] = useState<SubmissionItem[]>([]);
  const nextId = useRef(0);
  const queue = useRef<{ id: number; file: SubmissionFile }[]>([]);
  const active = useRef(0);
  const actorRef = useRef<Actor | null>(actor);
  actorRef.current = actor;
  const requestRefreshRef = useRef(requestRefresh);
  requestRefreshRef.current = requestRefresh;
  // 每次 submit/retry 批次内是否曾经成功过；批次结束时按结果通知一次刷新。
  const batchHadSuccessRef = useRef(false);

  const updateItem = useCallback((id: number, patch: Partial<SubmissionItem>) => {
    setItems((prev) => prev.map((i) => (i.id === id ? { ...i, ...patch } : i)));
  }, []);

  const enqueue = useCallback((files: readonly SubmissionFile[]) => {
    const newItems: SubmissionItem[] = files.map((f) => ({ id: nextId.current++, name: f.name, status: "pending", text: f.text }));
    setItems((prev) => [...prev, ...newItems]);
    queue.current.push(...newItems.map((it, i) => ({ id: it.id, file: files[i]! })));
    return newItems;
  }, []);

  const processOne = useCallback(async () => {
    if (active.current >= concurrency) return;
    const next = queue.current.shift();
    if (!next) return;
    const a = actorRef.current;
    if (!a) return;
    active.current += 1;
    updateItem(next.id, { status: "submitting" });
    try {
      const res = await apiClient.createReview(a, {
        project_id: a.projectId,
        data_policy: DEFAULT_DATA_POLICY,
        text: next.file.text,
        source_name: basename(next.file.name),
      });
      updateItem(next.id, { status: "submitted", reviewId: res.review_id });
      batchHadSuccessRef.current = true;
    } catch (e) {
      const err = e as { message?: string; correlationId?: string };
      updateItem(next.id, { status: "failed", errorMessage: err.message ?? "提交失败", correlationId: err.correlationId ?? "" });
    } finally {
      active.current -= 1;
      if (queue.current.length > 0) void processOne();
    }
  }, [concurrency, updateItem]);

  const pump = useCallback(() => {
    for (let i = 0; i < concurrency; i += 1) void processOne();
  }, [concurrency, processOne]);

  const waitForDrain = useCallback(
    () =>
      new Promise<void>((resolve) => {
        const tick = () => {
          if (queue.current.length === 0 && active.current === 0) resolve();
          else setTimeout(tick, 20);
        };
        tick();
      }),
    [],
  );

  const submit = useCallback(
    async (files: readonly SubmissionFile[]) => {
      batchHadSuccessRef.current = false;
      enqueue(files);
      pump();
      await waitForDrain();
      // 整个批次完成后再统一通知一次刷新信号；与 ReviewsRefreshContext 自身的
      // 同 tick 合并叠加，确保并发多文件也只发一次 GET /api/v1/reviews。
      if (batchHadSuccessRef.current) requestRefreshRef.current();
    },
    [enqueue, pump, waitForDrain],
  );

  const retry = useCallback(
    async (id: number) => {
      const item = items.find((i) => i.id === id);
      if (!item || item.status !== "failed") return;
      batchHadSuccessRef.current = false;
      queue.current.push({ id, file: { name: item.name, text: item.text } });
      pump();
      await waitForDrain();
      if (batchHadSuccessRef.current) requestRefreshRef.current();
    },
    [items, pump, waitForDrain],
  );

  const summary: SubmissionSummary = {
    total: items.length,
    pending: items.filter((i) => i.status === "pending").length,
    submitting: items.filter((i) => i.status === "submitting").length,
    submitted: items.filter((i) => i.status === "submitted").length,
    completed: items.filter((i) => i.status === "submitted").length,
    failed: items.filter((i) => i.status === "failed").length,
  };

  return { items, summary, submit, retry };
}
