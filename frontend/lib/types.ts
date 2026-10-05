export type UserResponse = {
  id: string;
  email: string;
  workspace_id: string;
};

export type DocumentSummary = {
  id: string;
  title: string;
  source_type: "pdf" | "text" | "url";
  source_ref: string | null;
  status: "pending" | "processing" | "ready" | "failed";
  page_count: number | null;
  chunk_count: number;
  entity_count: number;
  error: string | null;
  created_at: string;
  queued?: boolean | null;
};

export type Progress = {
  status: DocumentSummary["status"];
  step: string;
  pct: number;
  message: string | null;
};

export type Citation = {
  document_id: string;
  document_title: string;
  chunk_id: string;
  page_number: number | null;
  cited_text: string;
  char_start: number;
  char_end: number;
};

export type AnswerSegment = { text: string; citations: Citation[] };

export type ChatResponse = {
  answer: string;
  segments: AnswerSegment[];
  citations: Citation[];
  retrieved_chunk_ids: string[];
};

export type GraphNode = {
  id: string;
  name: string;
  entity_type: string | null;
  degree: number;
};

export type GraphEdge = {
  id: string;
  source: string;
  target: string;
  relation: string;
  chunk_id: string | null;
  document_id: string | null;
  document_title: string | null;
};

export type GraphResponse = { nodes: GraphNode[]; edges: GraphEdge[] };

export type EntityEvidence = {
  relation: string;
  other_name: string;
  direction: "in" | "out";
  chunk_id: string | null;
  document_id: string | null;
  document_title: string | null;
  page_number: number | null;
  char_start: number | null;
  char_end: number | null;
  excerpt: string | null;
};

export type EntityDetail = {
  id: string;
  name: string;
  entity_type: string | null;
  evidence: EntityEvidence[];
};
