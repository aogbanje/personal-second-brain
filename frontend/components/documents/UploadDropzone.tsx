"use client";

import { useRef, useState } from "react";

import { api } from "@/lib/api-client";

type Mode = "pdf" | "url" | "text";

const TABS: { mode: Mode; label: string }[] = [
  { mode: "pdf", label: "PDF" },
  { mode: "url", label: "URL" },
  { mode: "text", label: "Paste" },
];

export function UploadDropzone({ onIngested }: { onIngested: () => void }) {
  const [mode, setMode] = useState<Mode>("pdf");
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      onIngested();
    } catch (err) {
      setError(err instanceof Error ? err.message : "ingest failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitFiles(files: FileList | null) {
    if (!files?.length) return;
    // Upload sequentially: each POST returns immediately (the worker does the
    // slow part), so there is nothing to gain from racing them.
    await run(async () => {
      for (const file of Array.from(files)) {
        await api.uploadPdf(file);
      }
      if (fileInput.current) fileInput.current.value = "";
    });
  }

  return (
    <section className="rounded-xl border border-neutral-800 bg-neutral-900/40 p-4">
      <div className="mb-3 flex gap-1 text-sm">
        {TABS.map((tab) => (
          <button
            key={tab.mode}
            onClick={() => setMode(tab.mode)}
            className={`rounded-md px-3 py-1.5 transition ${
              mode === tab.mode
                ? "bg-neutral-800 text-neutral-100"
                : "text-neutral-500 hover:text-neutral-300"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {mode === "pdf" && (
        <div
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            void submitFiles(event.dataTransfer.files);
          }}
          onClick={() => fileInput.current?.click()}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-6 py-10 text-center transition ${
            dragging
              ? "border-amber-400/60 bg-amber-400/5"
              : "border-neutral-700 hover:border-neutral-600"
          }`}
        >
          <p className="text-sm text-neutral-300">
            {busy ? "Uploading…" : "Drop a PDF here, or click to choose"}
          </p>
          <p className="mt-1 text-xs text-neutral-600">
            Parsing, chunking and embedding happen in the background.
          </p>
          <input
            ref={fileInput}
            type="file"
            accept="application/pdf"
            multiple
            hidden
            onChange={(event) => void submitFiles(event.target.files)}
          />
        </div>
      )}

      {mode === "url" && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (!url.trim()) return;
            void run(async () => {
              await api.ingestUrl(url.trim());
              setUrl("");
            });
          }}
          className="flex gap-2"
        >
          <input
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://example.com/article"
            className="flex-1 rounded-md border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm outline-none focus:border-neutral-500"
          />
          <button
            disabled={busy}
            className="rounded-md bg-neutral-100 px-4 py-2 text-sm font-medium text-neutral-900 disabled:opacity-50"
          >
            {busy ? "…" : "Fetch"}
          </button>
        </form>
      )}

      {mode === "text" && (
        <form
          onSubmit={(event) => {
            event.preventDefault();
            if (!text.trim()) return;
            void run(async () => {
              await api.ingestText(title.trim() || "Untitled note", text);
              setTitle("");
              setText("");
            });
          }}
          className="space-y-2"
        >
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Title"
            className="w-full rounded-md border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm outline-none focus:border-neutral-500"
          />
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Paste text…"
            rows={6}
            className="w-full rounded-md border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm outline-none focus:border-neutral-500"
          />
          <button
            disabled={busy}
            className="rounded-md bg-neutral-100 px-4 py-2 text-sm font-medium text-neutral-900 disabled:opacity-50"
          >
            {busy ? "…" : "Add"}
          </button>
        </form>
      )}

      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
    </section>
  );
}
