"use client";

import Link from "next/link";

import { parseSnippet } from "@/lib/snippet";
import type { SearchHit } from "@/lib/types";

/**
 * One search result.
 *
 * The link carries the hit's char offsets, so clicking through lands on the
 * document viewer with the passage already highlighted -- the same mechanism
 * chat citations use, pointing at the same offsets into `raw_text`.
 */
export function SearchResultCard({ hit }: { hit: SearchHit }) {
  const href = `/dashboard/${hit.document_id}?start=${hit.char_start}&end=${hit.char_end}`;

  return (
    <Link
      href={href}
      className="block rounded-xl border border-neutral-800 bg-neutral-900/40 p-4 transition hover:border-neutral-600"
    >
      <div className="flex items-center gap-2 text-xs text-neutral-500">
        <span className="truncate font-medium text-neutral-400">
          {hit.document_title}
        </span>
        {hit.page_number !== null && (
          <span className="shrink-0">p. {hit.page_number}</span>
        )}
      </div>

      <p className="mt-2 text-sm leading-6 text-neutral-400">
        {parseSnippet(hit.snippet).map((segment, index) =>
          segment.marked ? (
            <mark key={index} className="psb-match">
              {segment.text}
            </mark>
          ) : (
            <span key={index}>{segment.text}</span>
          ),
        )}
      </p>
    </Link>
  );
}
