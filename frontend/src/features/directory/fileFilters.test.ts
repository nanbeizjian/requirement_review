import { isMarkdownName, partitionFiles, type FileEntryInput } from "./fileFilters";

const mk = (name: string, size = 10): FileEntryInput => ({ name, size });

describe("isMarkdownName", () => {
  it.each([["x.md", true], ["X.MD", true], ["a.markdown", true], ["y.Markdown", true], ["z.txt", false], ["noext", false]])(
    "%s -> %s",
    (n, expected) => { expect(isMarkdownName(n)).toBe(expected); },
  );
});

describe("partitionFiles", () => {
  it("splits markdown from ignored and reports ignored count", () => {
    const out = partitionFiles([mk("a.md"), mk("b.txt"), mk("C.MARKDOWN"), mk("d.png")]);
    expect(out.markdown.map((f) => f.name)).toEqual(["a.md", "C.MARKDOWN"]);
    expect(out.ignoredCount).toBe(2);
  });
  it("returns empty arrays for empty input", () => {
    const out = partitionFiles([]);
    expect(out.markdown).toEqual([]);
    expect(out.ignoredCount).toBe(0);
  });
});
