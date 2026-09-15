const fmt = new Intl.DateTimeFormat("zh-CN", { dateStyle: "short", timeStyle: "short" });
export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : fmt.format(d);
}
