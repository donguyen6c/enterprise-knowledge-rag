export type User = {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  role: string;
  organization_id: number | null;
  department_id: number | null;
};

export type Organization = {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type AdminUser = User & {
  organization: number | null;
  organization_name: string | null;
  department: number | null;
  department_name: string | null;
  is_active: boolean;
  date_joined: string;
};

export type AdminUserPayload = {
  username: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  role?: "SYSTEM_ADMIN" | "ORG_ADMIN" | "EMPLOYEE";
  organization?: number | null;
};

export type AdminOrganizationPayload = {
  name: string;
  description: string;
};

export type RegisterPayload = {
  username: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  organization: number;
};

export type AuthPayload = {
  access: string;
  refresh: string;
  user: User;
};

export type RefreshPayload = {
  access: string;
  refresh?: string;
};

export type ChatSession = {
  id: number;
  title: string;
  is_active: boolean;
  message_count: number;
  created_at: string;
  updated_at: string;
  messages?: ChatMessage[];
};

export type Citation = {
  rank: number;
  chunk_id: number;
  chunk_index: number;
  document_id: number;
  document_title: string;
  page_number: number | null;
  distance: number;
  semantic_score: number;
  final_score: number;
  snippet: string;
};

export type ChatMessage = {
  id: number;
  role: "USER" | "ASSISTANT";
  content: string;
  metadata: {
    citations?: Citation[];
    retrieval_limit?: number;
  };
  created_at: string;
};

export type AskResponse = {
  session: ChatSession;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  answer: string;
  citations: Citation[];
};

export type DocumentItem = {
  id: number;
  organization_name: string;
  category: number | null;
  category_name: string | null;
  uploaded_by_email: string;
  title: string;
  description: string;
  download_url: string | null;
  original_filename: string;
  file_size: number | null;
  status: "UPLOADED" | "PROCESSING" | "READY" | "FAILED" | "ARCHIVED";
  visibility: "ORGANIZATION" | "DEPARTMENT" | "ROLE" | "PRIVATE";
  error_message: string;
  chunk_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type DocumentChunkItem = {
  id: number;
  document: number;
  document_title: string;
  chunk_index: number;
  page_number: number | null;
  section_title: string;
  token_count: number;
  content: string;
  metadata: Record<string, unknown>;
  has_embedding: boolean;
  created_at: string;
};

export type DocumentUploadPayload = {
  file: File;
  title: string;
  description: string;
  visibility: DocumentItem["visibility"];
  organization?: number;
};

const API_BASE = "/backend";

function withTrailingSlash(path: string) {
  const [pathname, query = ""] = path.split("?");
  const normalizedPath = pathname.endsWith("/") ? pathname : `${pathname}/`;

  return query ? `${normalizedPath}?${query}` : normalizedPath;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string
): Promise<T> {
  const headers = new Headers(options.headers);

  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${withTrailingSlash(path)}`, {
    ...options,
    headers
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const error = (await response.json()) as { detail?: string };
      message = error.detail || JSON.stringify(error);
    } catch {
      // Keep default message when response is not JSON.
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function login(email: string, password: string) {
  return request<AuthPayload>("/api/auth/login/", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export function fetchActiveOrganizations() {
  return request<Organization[]>("/api/auth/organizations/");
}

export function registerAccount(payload: RegisterPayload) {
  return request<{ id: number; email: string; username: string; role: string; organization: number | null }>(
    "/api/auth/register/",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export function refreshAccessToken(refresh: string) {
  return request<RefreshPayload>("/api/auth/refresh/", {
    method: "POST",
    body: JSON.stringify({ refresh })
  });
}

export function logoutSession(access: string, refresh: string) {
  return request<{ detail: string }>(
    "/api/auth/logout/",
    {
      method: "POST",
      body: JSON.stringify({ refresh })
    },
    access
  );
}

export function fetchSessions(token: string) {
  return request<ChatSession[]>("/api/chats/sessions/", {}, token);
}

export function fetchSession(token: string, sessionId: number) {
  return request<ChatSession>(`/api/chats/sessions/${sessionId}/`, {}, token);
}

export function askQuestion(
  token: string,
  payload: {
    question: string;
    session_id?: number;
    limit?: number;
  }
) {
  return request<AskResponse>(
    "/api/chats/ask/",
    {
      method: "POST",
      body: JSON.stringify(payload)
    },
    token
  );
}

export function fetchDocuments(token: string) {
  return request<DocumentItem[]>("/api/documents/", {}, token);
}

export function fetchDocumentChunks(token: string, documentId: number) {
  return request<DocumentChunkItem[]>(
    `/api/documents/${documentId}/chunks/`,
    {},
    token
  );
}

export function queueDocumentProcessing(token: string, documentId: number) {
  return request<DocumentItem>(
    `/api/documents/${documentId}/process/`,
    { method: "POST" },
    token
  );
}

export async function uploadDocument(
  token: string,
  payload: DocumentUploadPayload
) {
  const formData = new FormData();
  formData.set("file", payload.file);
  formData.set("title", payload.title);
  formData.set("description", payload.description);
  formData.set("visibility", payload.visibility);

  if (payload.organization) {
    formData.set("organization", String(payload.organization));
  }

  const response = await fetch(`${API_BASE}${withTrailingSlash("/api/documents/")}`, {
    method: "POST",
    headers: {Authorization: `Bearer ${token}`},
    body: formData
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const error = (await response.json()) as {detail?: string};
      message = error.detail || JSON.stringify(error);
    } catch {
      // Keep the default message when response is not JSON.
    }

    throw new Error(message);
  }

  return (await response.json()) as DocumentItem;
}

export async function downloadDocument(token: string, documentId: number) {
  const response = await fetch(
    `${API_BASE}${withTrailingSlash(`/api/documents/${documentId}/download/`)}`,
    {headers: {Authorization: `Bearer ${token}`}}
  );

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const error = (await response.json()) as {detail?: string};
      message = error.detail || JSON.stringify(error);
    } catch {
      // Keep the default message when response is not JSON.
    }

    throw new Error(message);
  }

  return response.blob();
}

export function fetchAdminUsers(token: string) {
  return request<AdminUser[]>("/api/auth/admin/users/", {}, token);
}

export function createAdminUser(token: string, payload: AdminUserPayload) {
  return request<AdminUser>(
    "/api/auth/admin/users/",
    {
      method: "POST",
      body: JSON.stringify(payload)
    },
    token
  );
}

export function updateAdminUser(
  token: string,
  userId: number,
  payload: Partial<AdminUserPayload> & {is_active?: boolean}
) {
  return request<AdminUser>(
    `/api/auth/admin/users/${userId}/`,
    {
      method: "PATCH",
      body: JSON.stringify(payload)
    },
    token
  );
}

export function fetchAdminOrganizations(token: string) {
  return request<Organization[]>("/api/auth/admin/organizations/", {}, token);
}

export function createAdminOrganization(
  token: string,
  payload: AdminOrganizationPayload
) {
  return request<Organization>(
    "/api/auth/admin/organizations/",
    {
      method: "POST",
      body: JSON.stringify(payload)
    },
    token
  );
}

export function updateAdminOrganization(
  token: string,
  organizationId: number,
  payload: Partial<AdminOrganizationPayload> & {is_active?: boolean}
) {
  return request<Organization>(
    `/api/auth/admin/organizations/${organizationId}/`,
    {
      method: "PATCH",
      body: JSON.stringify(payload)
    },
    token
  );
}
