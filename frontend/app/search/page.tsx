"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { SearchResultCard } from "@/components/search/SearchResultCard";
import { api } from "@/lib/api-client";
import type { SearchResponse } from "@/lib/types";

/**
 * Direct retrieval, no model in the loop.
 *
 * The query lives in the URL rather than in component state, so a search is
 * shareable, survives a reload, and the back button walks through previous
 * searches. That is why this route is driven by `?q=` and the input only writes
 * to the URL on submit.
 */
function SearchView() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const query = searchParams.get("q") ?? "";

  const [draft, setDraft] = useState(query);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Keep the box in step with the URL when it changes from outside this
  // component -- a back navigation, or a link into a saved search.
  useEffect(() => {
    setDraft(query);
  }, [query]);

  useEffect(() => {
    if (!query.trim()) {
      setData(null);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    api
      .search(query)
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setError(null);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "search failed");
        setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [query]);

  function submit() {
    const next = draft.trim();
    if (!next) return;
    // push, not replace: each search should be its own history entry.
    router.push(`/search?q=${encodeURIComponent(next)}`);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Search</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Find the passage, not the answer. Vector similarity fused with
          full-text — the same ranking chat draws its context from.
        </p>
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
        className="flex gap-2"
      >
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Search your library…"
          autoFocus
          className="w-full rounded-md border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm outline-none focus:border-neutral-500"
        />
        <button
          disabled={loading || draft.trim() === ""}
          className="shrink-0 rounded-md bg-neutral-100 px-4 py-2 text-sm font-medium text-neutral-900 disabled:opacity-50"
        >
          {loading ? "…" : "Search"}
        </button>
      </form>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {data && (
        <div className="space-y-3">
          <p className="text-xs text-neutral-600">
            {data.results.length === 0
              ? "No passages matched."
              : `${data.results.length} passage${
                  data.results.length === 1 ? "" : "s"
                }`}
          </p>
          {data.results.map((hit) => (
            <SearchResultCard key={hit.chunk_id} hit={hit} />
          ))}
        </div>
      )}

      {!data && !loading && !error && (
        <p className="rounded-xl border border-dashed border-neutral-800 px-6 py-12 text-center text-sm text-neutral-600">
          Search across every document you have ingested.
        </p>
      )}
    </div>
  );
}

export default function SearchPage() {
  // useSearchParams needs a boundary to keep the route prerenderable.
  return (
    <Suspense fallback={<p className="text-sm text-neutral-500">Loading…</p>}>
      <SearchView />
    </Suspense>
  );
}
