"use client";

import { useEffect, useRef, useState } from "react";

import { CitationCard } from "@/components/chat/CitationCard";
import { api } from "@/lib/api-client";
import type { ChatResponse, Citation } from "@/lib/types";

type Turn =
  | { role: "user"; question: string }
  | { role: "assistant"; response: ChatResponse }
  | { role: "error"; message: string };

/**
 * Numbers citations across a whole answer so the inline markers and the source
 * list agree. Claude can cite the same passage from several segments; those
 * collapse onto one number keyed by chunk + span.
 */
function numberCitations(response: ChatResponse) {
  const key = (c: Citation) => `${c.chunk_id}:${c.char_start}:${c.char_end}`;
  const numbers = new Map<string, number>();
  const ordered: Citation[] = [];

  for (const segment of response.segments) {
    for (const citation of segment.citations) {
      if (numbers.has(key(citation))) continue;
      numbers.set(key(citation), ordered.length + 1);
      ordered.push(citation);
    }
  }

  return { numberOf: (c: Citation) => numbers.get(key(c)) ?? 0, ordered };
}

function Answer({ response }: { response: ChatResponse }) {
  const { numberOf, ordered } = numberCitations(response);

  return (
    <div className="space-y-4">
      <div className="whitespace-pre-wrap text-[15px] leading-7 text-neutral-200">
        {response.segments.map((segment, index) => (
          <span key={index}>
            {segment.text}
            {segment.citations.map((citation, position) => (
              <sup
                key={position}
                title={citation.document_title}
                className="ml-0.5 rounded bg-amber-400/15 px-1 font-mono text-[10px] text-amber-300"
              >
                {numberOf(citation)}
              </sup>
            ))}
          </span>
        ))}
      </div>

      {ordered.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-wide text-neutral-600">
            Sources
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {ordered.map((citation, index) => (
              <CitationCard
                key={index}
                citation={citation}
                index={index + 1}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function ChatWindow() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, busy]);

  async function ask(event: React.FormEvent) {
    event.preventDefault();
    const asked = question.trim();
    if (!asked || busy) return;

    setTurns((prev) => [...prev, { role: "user", question: asked }]);
    setQuestion("");
    setBusy(true);

    try {
      const response = await api.ask(asked);
      setTurns((prev) => [...prev, { role: "assistant", response }]);
    } catch (err) {
      setTurns((prev) => [
        ...prev,
        {
          role: "error",
          message: err instanceof Error ? err.message : "request failed",
        },
      ]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-[calc(100vh-11rem)] flex-col">
      <div className="flex-1 space-y-6 overflow-y-auto pr-1">
        {turns.length === 0 && (
          <p className="rounded-xl border border-dashed border-neutral-800 px-6 py-12 text-center text-sm text-neutral-600">
            Ask something about your documents. Every claim comes back with the
            passage it came from.
          </p>
        )}

        {turns.map((turn, index) => {
          if (turn.role === "user") {
            return (
              <div key={index} className="flex justify-end">
                <p className="max-w-[80%] rounded-2xl bg-neutral-800 px-4 py-2 text-[15px]">
                  {turn.question}
                </p>
              </div>
            );
          }
          if (turn.role === "error") {
            return (
              <p
                key={index}
                className="rounded-lg bg-red-500/10 px-4 py-3 text-sm text-red-300"
              >
                {turn.message}
              </p>
            );
          }
          return <Answer key={index} response={turn.response} />;
        })}

        {busy && (
          <p className="text-sm text-neutral-500">Searching and reading…</p>
        )}
        <div ref={bottom} />
      </div>

      <form onSubmit={ask} className="mt-4 flex gap-2">
        <input
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="What do my documents say about…"
          className="flex-1 rounded-md border border-neutral-700 bg-neutral-950 px-4 py-2.5 text-sm outline-none focus:border-neutral-500"
        />
        <button
          disabled={busy}
          className="rounded-md bg-neutral-100 px-5 py-2.5 text-sm font-medium text-neutral-900 disabled:opacity-50"
        >
          Ask
        </button>
      </form>
    </div>
  );
}
