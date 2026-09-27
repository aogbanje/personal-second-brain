"use client";

import Link from "next/link";

import type { Citation } from "@/lib/types";

/**
 * A single source card. The link carries the citation's char offsets so the
 * viewer can highlight the exact passage rather than just opening the document.
 */
export function CitationCard({
  citation,
  index,
}: {
  citation: Citation;
  index: number;
}) {
  const href = `/dashboard/${citation.document_id}?start=${citation.char_start}&end=${citation.char_end}`;

  return (
    <Link
      href={href}
      className="block rounded-lg border border-neutral-800 bg-neutral-900/60 p-3 transition hover:border-neutral-600"
    >
      <div className="flex items-center gap-2 text-xs text-neutral-500">
        <span className="rounded bg-neutral-800 px-1.5 py-0.5 font-mono text-[10px] text-neutral-400">
          {index}
        </span>
        <span className="truncate">{citation.document_title}</span>
        {citation.page_number !== null && (
          <span className="shrink-0">p. {citation.page_number}</span>
        )}
      </div>
      <p className="mt-2 line-clamp-4 text-sm leading-6 text-neutral-400">
        “{citation.cited_text}”
      </p>
    </Link>
  );
}
