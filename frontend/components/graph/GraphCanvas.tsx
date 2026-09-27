"use client";

import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo } from "react";

import type { GraphResponse } from "@/lib/types";

const TYPE_COLORS: Record<string, string> = {
  person: "#f59e0b",
  organization: "#38bdf8",
  concept: "#a78bfa",
  place: "#34d399",
  product: "#fb7185",
  event: "#facc15",
};

const DEFAULT_COLOR = "#a3a3a3";

/**
 * Concentric-ring layout, most-connected first.
 *
 * Deliberately not a force simulation: this is deterministic, costs nothing,
 * and puts the hubs where you look first. Ring capacity grows outward so the
 * spacing stays roughly even.
 */
function layout(graph: GraphResponse): Node[] {
  const ordered = [...graph.nodes].sort((a, b) => b.degree - a.degree);
  const maxDegree = Math.max(1, ...ordered.map((node) => node.degree));

  const positions: Node[] = [];
  let index = 0;
  let ring = 0;

  while (index < ordered.length) {
    const capacity = ring === 0 ? 1 : ring * 6;
    const radius = ring * 190;
    const count = Math.min(capacity, ordered.length - index);

    for (let slot = 0; slot < count; slot += 1) {
      const node = ordered[index + slot];
      const angle = (slot / count) * Math.PI * 2;
      const color = TYPE_COLORS[node.entity_type ?? ""] ?? DEFAULT_COLOR;
      const weight = node.degree / maxDegree;

      positions.push({
        id: node.id,
        position: {
          x: Math.cos(angle) * radius,
          y: Math.sin(angle) * radius,
        },
        data: { label: node.name },
        style: {
          background: "#171717",
          border: `1px solid ${color}`,
          borderRadius: 999,
          color: "#e5e5e5",
          fontSize: 11 + Math.round(weight * 4),
          padding: "6px 12px",
          width: "auto",
        },
      });
    }

    index += count;
    ring += 1;
  }

  return positions;
}

function toEdges(graph: GraphResponse): Edge[] {
  return graph.edges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    label: edge.relation,
    animated: false,
    style: { stroke: "#404040" },
    labelStyle: { fill: "#737373", fontSize: 10 },
    labelBgStyle: { fill: "#0a0a0a" },
  }));
}

export function GraphCanvas({
  graph,
  onSelect,
}: {
  graph: GraphResponse;
  onSelect: (entityId: string) => void;
}) {
  const nodes = useMemo(() => layout(graph), [graph]);
  const edges = useMemo(() => toEdges(graph), [graph]);

  return (
    <div className="h-[calc(100vh-14rem)] overflow-hidden rounded-xl border border-neutral-800 bg-neutral-950">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodeClick={(_, node) => onSelect(node.id)}
        fitView
        proOptions={{ hideAttribution: true }}
        minZoom={0.1}
      >
        <Background color="#262626" gap={24} />
        <Controls className="!bg-neutral-900 !border-neutral-800" />
        <MiniMap
          pannable
          zoomable
          maskColor="rgba(10,10,10,0.7)"
          nodeColor={() => "#525252"}
          style={{ background: "#171717" }}
        />
      </ReactFlow>
    </div>
  );
}
