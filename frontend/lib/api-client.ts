import type {
  ChatResponse,
  DocumentSummary,
  EntityDetail,
  GraphResponse,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body && !(init.body instanceof FormData)
        ? { "content-type": "application/json" }
        : {}),
      ...init?.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    // FastAPI puts the useful part in `detail`; surface it rather than a bare code.
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, response.status);
  }

  return response.status === 204 ? (undefined as T) : response.json();
}

export const api = {
  listDocuments: () => request<DocumentSummary[]>("/documents"),

  getDocument: (id: string) => request<DocumentSummary>(`/documents/${id}`),

  getDocumentText: (id: string) =>
    request<{ id: string; title: string; text: string }>(`/documents/${id}/text`),

  uploadPdf: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<DocumentSummary>("/documents", { method: "POST", body });
  },

  ingestUrl: (url: string) =>
    request<DocumentSummary>("/documents/url", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

  ingestText: (title: string, text: string) =>
    request<DocumentSummary>("/documents/text", {
      method: "POST",
      body: JSON.stringify({ title, text }),
    }),

  reindex: (id: string) =>
    request<DocumentSummary>(`/documents/${id}/reindex`, { method: "POST" }),

  deleteDocument: (id: string) =>
    request<void>(`/documents/${id}`, { method: "DELETE" }),

  ask: (question: string) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ question }),
    }),

  getGraph: (documentId?: string) =>
    request<GraphResponse>(
      `/graph${documentId ? `?document_id=${documentId}` : ""}`,
    ),

  getEntity: (id: string) => request<EntityDetail>(`/graph/entities/${id}`),
};

export const eventsUrl = (docId: string) =>
  `${API_BASE}/documents/${docId}/events`;
