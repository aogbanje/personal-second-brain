import { redirectToLogin } from "./auth";
import type {
  ChatResponse,
  DocumentSummary,
  EntityDetail,
  GraphResponse,
  UserResponse,
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
    // The session is an httpOnly cookie on a different port, so every request
    // is cross-origin and needs this to carry it. The backend answers with
    // allow_credentials and an explicit origin.
    credentials: "include",
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

    // An expired session should land on the login screen rather than surfacing
    // as "not signed in" on whatever page happened to be open. Auth routes are
    // exempt: a failed login has to render its own error, not bounce.
    if (response.status === 401 && !path.startsWith("/auth/")) {
      redirectToLogin();
    }

    throw new ApiError(detail, response.status);
  }

  return response.status === 204 ? (undefined as T) : response.json();
}

export const api = {
  signup: (email: string, password: string) =>
    request<UserResponse>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<UserResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  logout: () => request<void>("/auth/logout", { method: "POST" }),

  me: () => request<UserResponse>("/auth/me"),

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
