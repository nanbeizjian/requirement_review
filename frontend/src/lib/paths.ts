/** Extract basename from a File or path-like string. Never exposes absolute paths. */
export function basename(input: string): string {
  const norm = input.replace(/\\/g, "/");
  const idx = norm.lastIndexOf("/");
  return idx === -1 ? norm : norm.slice(idx + 1);
}
