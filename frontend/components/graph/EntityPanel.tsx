"use client";

import Link from "next/link";

import type { EntityDetail } from "@/lib/types";

/**
 * Side panel for a clicked entity. Every relation shown here is backed by the
 * chunk it was extracted from, so each row links straight to the highlighted
 * passage -- the graph is checkable, not just pretty.
 */
export function EntityPanel({
  entity,
  loading,
  onClose,
}: {
  entity: EntityDetail | null;
  loading: boolean;
  onClose: () => void;
}) {
  if (!loading && !entity) return null;

  return (
    <aside className="rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
      {loading || !entity ? (
        <p className="text-sm text-neutral-500">Loading…</p>
      ) : (
        <>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="font-medium">{entity.name}</h2>
              {entity.entity_type && (
                <p className="mt-0.5 text-xs text-neutral-500">
                  {entity.entity_type}
                </p>
              )}
            </div>
            <button
              onClick={onClose}
              className="text-xs text-neutral-500 hover:text-neutral-300"
            >
              Close
            </button>
          </div>

          <div className="mt-4 space-y-2">
            {entity.evidence.length === 0 && (
              <p className="text-sm text-neutral-600">No relations recorded.</p>
            )}
            {entity.evidence.map((item, index) => {
              const body = (
                <>
                  <p className="text-sm text-neutral-300">
                    {item.direction === "out" ? (
                      <>
                        <span className="text-neutral-500">
                          {item.relation}
                        </span>{" "}
                        → {item.other_name}
                      </>
                    ) : (
                      <>
                        {item.other_name} →{" "}
                        <span className="text-neutral-500">
                          {item.relation}
                        </span>
                      </>
                    )}
                  </p>
                  {item.excerpt && (
                    <p className="mt-1 line-clamp-3 text-xs leading-5 text-neutral-500">
                      “{item.excerpt}”
                    </p>
                  )}
                  {item.document_title && (
                    <p className="mt-1 text-[11px] text-neutral-600">
                      {item.document_title}
                      {item.page_number !== null
                        ? ` · p. ${item.page_number}`
                        : ""}
                    </p>
                  )}
                </>
              );

              const linkable =
                item.document_id !== null &&
                item.char_start !== null &&
                item.char_end !== null;

              return linkable ? (
                <Link
                  key={index}
                  href={`/dashboard/${item.document_id}?start=${item.char_start}&end=${item.char_end}`}
                  className="block rounded-lg border border-neutral-800 p-3 transition hover:border-neutral-600"
                >
                  {body}
                </Link>
              ) : (
                <div
                  key={index}
                  className="rounded-lg border border-neutral-800 p-3"
                >
                  {body}
                </div>
              );
            })}
          </div>
        </>
      )}
    </aside>
  );
}
