"use client";

import { DocumentCard } from "@/components/documents/DocumentCard";
import { UploadDropzone } from "@/components/documents/UploadDropzone";
import { useDocuments } from "@/hooks/useDocuments";

export default function DashboardPage() {
  const { documents, loading, error, refresh } = useDocuments();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Library</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Everything here is searchable from Chat and appears in the Graph.
        </p>
      </div>

      <UploadDropzone onIngested={refresh} />

      {error && <p className="text-sm text-red-400">{error}</p>}

      {loading ? (
        <p className="text-sm text-neutral-500">Loading…</p>
      ) : documents.length === 0 ? (
        <p className="rounded-xl border border-dashed border-neutral-800 px-6 py-12 text-center text-sm text-neutral-600">
          Nothing ingested yet.
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {documents.map((doc) => (
            <DocumentCard key={doc.id} doc={doc} onChanged={refresh} />
          ))}
        </div>
      )}
    </div>
  );
}
