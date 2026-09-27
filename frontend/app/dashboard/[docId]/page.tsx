"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { api } from "@/lib/api-client";

type Doc = { id: string; title: string; text: string };

/**
 * Renders the document text with one span highlighted.
 *
 * `start`/`end` are absolute offsets into the same `raw_text` the chunker
 * measured against, so no re-matching or fuzzy search is needed -- the citation
 * lands exactly where the model said it did.
 */
function Highlighted({
  text,
  start,
  end,
}: {
  text: string;
  start: number | null;
  end: number | null;
}) {
  const mark = useRef<HTMLElement>(null);

  useEffect(() => {
    mark.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [start, end]);

  const valid =
    start !== null &&
    end !== null &&
    start >= 0 &&
    end > start &&
    start < text.length;

  if (!valid) {
    return <>{text}</>;
  }

  const stop = Math.min(end, text.length);
  return (
    <>
      {text.slice(0, start)}
      <mark ref={mark} className="psb-highlight">
        {text.slice(start, stop)}
      </mark>
      {text.slice(stop)}
    </>
  );
}

function toOffset(raw: string | null): number | null {
  if (raw === null) return null;
  const parsed = Number.parseInt(raw, 10);
  return Number.isNaN(parsed) ? null : parsed;
}

function Viewer() {
  const { docId } = useParams<{ docId: string }>();
  const search = useSearchParams();
  const [doc, setDoc] = useState<Doc | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .getDocumentText(docId)
      .then((data) => {
        if (!cancelled) setDoc(data);
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "could not load");
      });
    return () => {
      cancelled = true;
    };
  }, [docId]);

  if (error) return <p className="text-sm text-red-400">{error}</p>;
  if (!doc) return <p className="text-sm text-neutral-500">Loading…</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-baseline justify-between gap-4">
        <h1 className="text-xl font-semibold tracking-tight">{doc.title}</h1>
        <Link
          href="/dashboard"
          className="shrink-0 text-sm text-neutral-500 hover:text-neutral-300"
        >
          ← Library
        </Link>
      </div>

      {doc.text.trim() === "" ? (
        <p className="rounded-xl border border-dashed border-neutral-800 px-6 py-12 text-center text-sm text-neutral-600">
          No text extracted for this document.
        </p>
      ) : (
        <article className="whitespace-pre-wrap rounded-xl border border-neutral-800 bg-neutral-900/40 p-6 font-serif text-[15px] leading-7 text-neutral-300">
          <Highlighted
            text={doc.text}
            start={toOffset(search.get("start"))}
            end={toOffset(search.get("end"))}
          />
        </article>
      )}
    </div>
  );
}

export default function DocumentPage() {
  // useSearchParams needs a Suspense boundary to keep the route prerenderable.
  return (
    <Suspense fallback={<p className="text-sm text-neutral-500">Loading…</p>}>
      <Viewer />
    </Suspense>
  );
}
