export interface FileEntryInput {
  name: string;
  size: number;
}

export interface FileEntry extends FileEntryInput {
  basename: string;
}

const MD_EXT = /\.(md|markdown)$/i;

export function isMarkdownName(name: string): boolean {
  return MD_EXT.test(name);
}

export function partitionFiles(inputs: readonly FileEntryInput[]): { markdown: FileEntry[]; ignoredCount: number } {
  const markdown: FileEntry[] = [];
  let ignoredCount = 0;
  for (const i of inputs) {
    if (isMarkdownName(i.name)) markdown.push({ ...i, basename: i.name });
    else ignoredCount += 1;
  }
  return { markdown, ignoredCount };
}
