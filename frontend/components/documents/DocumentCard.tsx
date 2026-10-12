"use client";

import Link from "next/link";
import { useState } from "react";

import { useIngestProgress } from "@/hooks/useIngestProgress";
import { api } from "@/lib/api-client";
import type { DocumentSummary } from "@/lib/types";

const STATUS_STYLES: Record<DocumentSummary["status"], string> = {
  pending: "bg-neutral-700/40 text-neutral-300",
  processing: "bg-sky-500/15 text-sky-300",
  ready: "bg-emerald-500/15 text-emerald-300",
  failed: "bg-red-500/15 text-red-300",
};

const SOURCE_LABEL: Record<DocumentSummary["source_type"], string> = {
  pdf: "PDF",
  url: "Web",
  text: "Note",
};

export function DocumentCard({
  doc,
  onChanged,
}: {
  doc: DocumentSummary;
  onChanged: () => void;
}) {
  const progress = useIngestProgress(doc, onChanged);
  const [busy, setBusy] = useState(false);

  const status = progress?.status ?? doc.status;
  const settled = status === "ready" || status === "failed";

  async function act(action: () => Promise<unknown>) {
    setBusy(true);
    try {
      await action();
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <Link
            href={`/dashboard/${doc.id}`}
            className="block truncate font-medium hover:underline"
          >
            {doc.title}
          </Link>
          <p className="mt-1 truncate text-xs text-neutral-500">
            {SOURCE_LABEL[doc.source_type]}
            {doc.source_ref ? ` · ${doc.source_ref}` : ""}
          </p>
        </div>
        <span
          className={`shrink-0 rounded-full px-2 py-0.5 text-xs ${STATUS_STYLES[status]}`}
        >
          {progress && !settled ? progress.step : status}
        </span>
      </div>

      {!settled && (
        <div className="mt-3 h-1 overflow-hidden rounded-full bg-neutral-800">
          <div
            className="h-full bg-sky-400 transition-all duration-500"
            style={{ width: `${progress?.pct ?? 5}%` }}
          />
        </div>
      )}

      {status === "failed" && (doc.error || progress?.message) && (
        <p className="mt-3 rounded-md bg-red-500/5 px-3 py-2 text-xs text-red-300">
          {progress?.message ?? doc.error}
        </p>
      )}

      <div className="mt-4 flex items-center justify-between text-xs text-neutral-500">
        <span>
          {doc.chunk_count} chunks
          {doc.page_count ? ` · ${doc.page_count} pages` : ""}
          {doc.entity_count ? ` · ${doc.entity_count} entities` : ""}
        </span>
        <span className="flex gap-3">
          <button
            disabled={busy}
            onClick={() => void act(() => api.reindex(doc.id))}
            className="hover:text-neutral-200 disabled:opacity-40"
          >
            Reindex
          </button>
          <button
            disabled={busy}
            onClick={() => void act(() => api.deleteDocument(doc.id))}
            className="hover:text-red-300 disabled:opacity-40"
          >
            Delete
          </button>
        </span>
      </div>
    </article>
  );
}
