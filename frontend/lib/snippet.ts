/**
 * Splitting the backend's snippet sentinels into safe segments.
 *
 * The backend returns excerpts with matched terms wrapped in two control
 * characters rather than `<mark>` tags, because Postgres' `ts_headline` does not
 * escape the text it highlights -- see `retrieval/snippets.py`. So the marks
 * arrive as data, get split here, and become real React elements. Nothing is
 * ever handed to `dangerouslySetInnerHTML`, which means an ingested document
 * full of `<script>` is just text.
 *
 * These two constants must match MARK_START/MARK_END in that module.
 */

const MARK_START = "\x02";
const MARK_END = "\x03";

export type SnippetSegment = { text: string; marked: boolean };

/**
 * Turn a sentinel-marked snippet into alternating plain/marked runs.
 *
 * Tolerant by design: unmatched or stray sentinels are dropped rather than
 * throwing, because the input is derived from arbitrary document text and a
 * malformed excerpt should degrade to unhighlighted prose, not break the page.
 */
export function parseSnippet(snippet: string): SnippetSegment[] {
  const segments: SnippetSegment[] = [];
  let rest = snippet;

  while (rest.length > 0) {
    const start = rest.indexOf(MARK_START);
    if (start === -1) break;

    const end = rest.indexOf(MARK_END, start + 1);
    // An opener with no closer: treat the rest as plain text.
    if (end === -1) break;

    if (start > 0) segments.push({ text: rest.slice(0, start), marked: false });
    const marked = rest.slice(start + 1, end);
    if (marked) segments.push({ text: marked, marked: true });
    rest = rest.slice(end + 1);
  }

  if (rest.length > 0) {
    // Strip any sentinel that survived the loop so control characters never
    // reach the DOM.
    const tail = rest.split(MARK_START).join("").split(MARK_END).join("");
    if (tail) segments.push({ text: tail, marked: false });
  }

  return segments;
}
