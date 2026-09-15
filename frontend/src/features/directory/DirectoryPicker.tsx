import { useCallback, useRef, useState } from "react";
import { partitionFiles } from "./fileFilters";
import { Button } from "../../components/Button/Button";
import { FileEntryList } from "./FileEntryList";
import { useDirectorySubmission } from "./useDirectorySubmission";
import styles from "./DirectoryPicker.module.css";

export interface ReadyFile { name: string; text: string; size: number }

interface Props { onReady?: (files: ReadyFile[]) => void }

const MAX_BYTES = 1_000_000;

async function readUtf8(file: File): Promise<string> {
  if (file.size > MAX_BYTES) throw new Error(`文件过大: ${file.name}`);
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onerror = () => reject(new Error(`读取失败: ${file.name}`));
    r.onload = () => resolve(String(r.result ?? ""));
    r.readAsText(file, "utf-8");
  });
}

export function DirectoryPicker({ onReady }: Props) {
  const dirRef = useRef<HTMLInputElement>(null);
  const filesRef = useRef<HTMLInputElement>(null);
  const [ignored, setIgnored] = useState(0);
  const [ready, setReady] = useState<ReadyFile[]>([]);
  const { items, summary, submit, retry } = useDirectorySubmission({ concurrency: 3 });

  const ingest = useCallback(async (fl: FileList | null) => {
    if (!fl) return;
    const arr = Array.from(fl);
    const { markdown, ignoredCount } = partitionFiles(arr.map((f) => ({ name: f.name, size: f.size })));
    setIgnored(ignoredCount);
    const withText: ReadyFile[] = [];
    for (const meta of markdown) {
      const file = arr.find((f) => f.name === meta.name);
      if (!file) continue;
      try {
        const text = await readUtf8(file);
        withText.push({ name: meta.name, text, size: meta.size });
      } catch {
        withText.push({ name: meta.name, text: "", size: meta.size });
      }
    }
    setReady(withText);
    onReady?.(withText);
  }, [onReady]);

  return (
    <section aria-labelledby="dir-h" className={styles.wrap}>
      <h2 id="dir-h">选择本地需求目录</h2>
      <div className={styles.controls}>
        <label className={styles.field}>
          <span>目录（推荐）</span>
          <input
            ref={dirRef}
            data-testid="dir-input"
            type="file"
            // @ts-expect-error non-standard but supported in Chromium/Safari/Firefox
            webkitdirectory=""
            multiple
            onChange={(e) => ingest(e.currentTarget.files)}
          />
        </label>
        <label className={styles.field}>
          <span>多文件回退</span>
          <input
            ref={filesRef}
            data-testid="files-input"
            type="file"
            accept=".md,.markdown,text/markdown"
            multiple
            onChange={(e) => ingest(e.currentTarget.files)}
          />
        </label>
      </div>
      {ignored > 0 ? <p className={styles.ignored}>忽略 {ignored} 个非 Markdown 文件</p> : null}
      {ready.length > 0 ? (
        <>
          <p className={styles.summary}>将提交 {ready.length} 份 Markdown 文件</p>
          <Button onClick={() => submit(ready)} disabled={summary.pending + summary.submitting > 0}>
            开始提交
          </Button>
          <FileEntryList items={items} onRetry={retry} />
        </>
      ) : null}
    </section>
  );
}
