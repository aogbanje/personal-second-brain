"use client";

import { useEffect, useState } from "react";

import { eventsUrl } from "@/lib/api-client";
import type { DocumentSummary, Progress } from "@/lib/types";

const TERMINAL = new Set(["ready", "failed"]);

/**
 * Subscribes to a document's ingestion progress over SSE.
 *
 * The backend replays the current state on connect, so mounting this late (a
 * page reload mid-ingest) still shows the truth rather than an empty bar.
 * `onSettled` fires once the document reaches a terminal state so the caller
 * can refresh the row's real counts.
 */
export function useIngestProgress(
  doc: DocumentSummary,
  onSettled: () => void,
): Progress | null {
  const [progress, setProgress] = useState<Progress | null>(null);

  useEffect(() => {
    if (TERMINAL.has(doc.status)) {
      setProgress(null);
      return;
    }

    // withCredentials is what carries the session cookie. EventSource cannot
    // set headers at all, which is precisely why the session is a cookie and
    // not a bearer token.
    const source = new EventSource(eventsUrl(doc.id), {
      withCredentials: true,
    });

    source.addEventListener("progress", (event) => {
      const payload = JSON.parse((event as MessageEvent).data) as Progress;
      setProgress(payload);
      if (TERMINAL.has(payload.status)) {
        source.close();
        onSettled();
      }
    });

    // A dropped stream should not strand the row on a stale bar; fall back to
    // the list refresh, which reads the persisted status.
    source.onerror = () => {
      source.close();
      onSettled();
    };

    return () => source.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc.id, doc.status]);

  return progress;
}
