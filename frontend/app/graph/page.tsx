"use client";

import { useState } from "react";

import { EntityPanel } from "@/components/graph/EntityPanel";
import { GraphCanvas } from "@/components/graph/GraphCanvas";
import { useDocuments } from "@/hooks/useDocuments";
import { useGraphData } from "@/hooks/useGraphData";
import { api } from "@/lib/api-client";
import type { EntityDetail } from "@/lib/types";

export default function GraphPage() {
  const [documentId, setDocumentId] = useState<string>("");
  const { documents } = useDocuments();
  const { graph, loading, error } = useGraphData(documentId || undefined);

  const [entity, setEntity] = useState<EntityDetail | null>(null);
  const [entityLoading, setEntityLoading] = useState(false);

  async function select(entityId: string) {
    setEntityLoading(true);
    setEntity(null);
    try {
      setEntity(await api.getEntity(entityId));
    } finally {
      setEntityLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Graph</h1>
          <p className="mt-1 text-sm text-neutral-500">
            {graph.nodes.length} entities · {graph.edges.length} relations
          </p>
        </div>
        <select
          value={documentId}
          onChange={(event) => {
            setDocumentId(event.target.value);
            setEntity(null);
          }}
          className="rounded-md border border-neutral-700 bg-neutral-950 px-3 py-2 text-sm outline-none focus:border-neutral-500"
        >
          <option value="">All documents</option>
          {documents
            .filter((doc) => doc.entity_count > 0)
            .map((doc) => (
              <option key={doc.id} value={doc.id}>
                {doc.title}
              </option>
            ))}
        </select>
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="grid gap-4 lg:grid-cols-[1fr_22rem]">
        {loading ? (
          <p className="text-sm text-neutral-500">Loading…</p>
        ) : graph.nodes.length === 0 ? (
          <p className="rounded-xl border border-dashed border-neutral-800 px-6 py-12 text-center text-sm text-neutral-600">
            No entities extracted yet. Ingest a document first.
          </p>
        ) : (
          <GraphCanvas graph={graph} onSelect={(id) => void select(id)} />
        )}

        <EntityPanel
          entity={entity}
          loading={entityLoading}
          onClose={() => setEntity(null)}
        />
      </div>
    </div>
  );
}
