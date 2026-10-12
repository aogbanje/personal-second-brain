"use client";

import { useCallback, useEffect, useState } from "react";

import { api } from "@/lib/api-client";
import type { GraphResponse } from "@/lib/types";

const EMPTY: GraphResponse = { nodes: [], edges: [] };

export function useGraphData(documentId?: string) {
  const [graph, setGraph] = useState<GraphResponse>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      setGraph(await api.getGraph(documentId));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "could not load graph");
      setGraph(EMPTY);
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { graph, loading, error, refresh };
}
