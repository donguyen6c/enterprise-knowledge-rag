"use client";

import {
  BookOpen,
  Bot,
  FileText,
  LogOut,
  MessageSquarePlus,
  LoaderCircle,
  Play,
  RefreshCw,
  RotateCcw,
  Search,
  Send,
  UserRound
} from "lucide-react";
import {
  FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";
import {
  askQuestion,
  ChatMessage,
  ChatSession,
  Citation,
  DocumentChunkItem,
  DocumentItem,
  fetchDocumentChunks,
  fetchDocuments,
  fetchSession,
  fetchSessions,
  login,
  logoutSession,
  queueDocumentProcessing,
  refreshAccessToken,
  User
} from "@/lib/api";

const AUTH_KEY = "ekr.auth";

type StoredAuth = {
  access: string;
  refresh: string;
  user: User;
};

function readStoredAuth(): StoredAuth | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.localStorage.getItem(AUTH_KEY);

  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as StoredAuth;
  } catch {
    window.localStorage.removeItem(AUTH_KEY);
    return null;
  }
}

function accessTokenExpiresAt(token: string) {
  try {
    const payload = token.split(".")[1];
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    const decoded = JSON.parse(window.atob(padded)) as { exp?: number };

    return decoded.exp ? decoded.exp * 1000 : null;
  } catch {
    return null;
  }
}

function formatTime(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit"
  }).format(new Date(value));
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric"
  }).format(new Date(value));
}

function formatFileSize(value: number | null) {
  if (!value) {
    return "0 KB";
  }

  if (value < 1024 * 1024) {
    return `${Math.ceil(value / 1024)} KB`;
  }

  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function statusLabel(status: DocumentItem["status"]) {
  const labels: Record<DocumentItem["status"], string> = {
    UPLOADED: "Đang chờ",
    PROCESSING: "Đang xử lý",
    READY: "Sẵn sàng",
    FAILED: "Lỗi",
    ARCHIVED: "Đã lưu trữ"
  };

  return labels[status];
}

function CitationList({ citations }: { citations?: Citation[] }) {
  if (!citations?.length) {
    return null;
  }

  return (
    <div className="citations">
      {citations.slice(0, 3).map((citation) => (
        <div className="citation" key={`${citation.chunk_id}-${citation.rank}`}>
          <div className="citation-top">
            <span>#{citation.rank}</span>
            <span>
              Doc {citation.document_id}
              {citation.page_number ? ` · Trang ${citation.page_number}` : ""}
            </span>
          </div>
          <div className="citation-title">{citation.document_title}</div>
          <div className="citation-snippet">{citation.snippet}</div>
        </div>
      ))}
    </div>
  );
}

function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "USER";
  const citations = message.metadata?.citations;

  return (
    <div className={`message-row ${isUser ? "user" : "assistant"}`}>
      <article className="message">
        <header className="message-header">
          <span>{isUser ? "Bạn" : "RAG"}</span>
          <span>{formatTime(message.created_at)}</span>
        </header>
        <div className="message-content">{message.content}</div>
        {!isUser && <CitationList citations={citations} />}
      </article>
    </div>
  );
}

function StatusBadge({ status }: { status: DocumentItem["status"] }) {
  return (
    <span className={`status-badge ${status.toLowerCase()}`}>
      {statusLabel(status)}
    </span>
  );
}

function DocumentManager({
  documents,
  filteredDocuments,
  chunks,
  selectedDocument,
  documentSearch,
  documentError,
  loadingDocuments,
  loadingChunks,
  canManageDocuments,
  processingDocumentId,
  onSearchChange,
  onProcessDocument,
  onRefresh,
  onSelectDocument
}: {
  documents: DocumentItem[];
  filteredDocuments: DocumentItem[];
  chunks: DocumentChunkItem[];
  selectedDocument?: DocumentItem;
  documentSearch: string;
  documentError: string;
  loadingDocuments: boolean;
  loadingChunks: boolean;
  canManageDocuments: boolean;
  processingDocumentId: number | null;
  onSearchChange: (value: string) => void;
  onProcessDocument: (documentId: number) => void;
  onRefresh: () => void;
  onSelectDocument: (documentId: number) => void;
}) {
  const readyCount = documents.filter((document) => document.status === "READY").length;
  const failedCount = documents.filter((document) => document.status === "FAILED").length;
  const processingCount = documents.filter(
    (document) => document.status === "PROCESSING" || document.status === "UPLOADED"
  ).length;

  return (
    <section className="documents-view">
      <div className="documents-toolbar">
        <div className="document-metrics" aria-label="Thống kê tài liệu">
          <span>{documents.length} tài liệu</span>
          <span>{readyCount} sẵn sàng</span>
          <span>{failedCount} lỗi</span>
          <span>{processingCount} chờ xử lý</span>
        </div>
        <label className="document-search">
          <Search size={16} />
          <input
            aria-label="Tìm tài liệu"
            onChange={(event) => onSearchChange(event.target.value)}
            placeholder="Tìm theo tên, loại, trạng thái..."
            value={documentSearch}
          />
        </label>
        <button
          className="icon-button light"
          disabled={loadingDocuments}
          onClick={onRefresh}
          title="Tải lại tài liệu"
          type="button"
        >
          <RefreshCw size={17} />
        </button>
      </div>

      {documentError ? <div className="error-box">{documentError}</div> : null}

      <div className="documents-grid">
        <div className="document-list-panel">
          {loadingDocuments ? (
            <div className="loading-line">Đang tải tài liệu...</div>
          ) : filteredDocuments.length === 0 ? (
            <div className="empty-panel">Không có tài liệu phù hợp.</div>
          ) : (
            filteredDocuments.map((document) => (
              <button
                className={`document-row ${
                  document.id === selectedDocument?.id ? "active" : ""
                }`}
                key={document.id}
                onClick={() => onSelectDocument(document.id)}
                type="button"
              >
                <div>
                  <strong>{document.title}</strong>
                  <span>
                    Doc {document.id} · {document.category_name || "Chưa phân loại"}
                  </span>
                </div>
                <div className="document-row-meta">
                  <StatusBadge status={document.status} />
                  <span>{document.chunk_count} chunks</span>
                </div>
              </button>
            ))
          )}
        </div>

        <div className="chunk-panel">
          {selectedDocument ? (
            <>
              <div className="document-detail">
                <div>
                  <span className="eyebrow">Doc {selectedDocument.id}</span>
                  <h2>{selectedDocument.title}</h2>
                  <p>
                    {selectedDocument.category_name || "Chưa phân loại"} ·{" "}
                    {selectedDocument.visibility} ·{" "}
                    {formatFileSize(selectedDocument.file_size)}
                  </p>
                </div>
                <div className="document-detail-actions">
                  <StatusBadge status={selectedDocument.status} />
                  {canManageDocuments && selectedDocument.status !== "ARCHIVED" ? (
                    <button
                      className="text-button document-action"
                      disabled={
                        selectedDocument.status === "PROCESSING" ||
                        selectedDocument.status === "UPLOADED" ||
                        processingDocumentId === selectedDocument.id
                      }
                      onClick={() => onProcessDocument(selectedDocument.id)}
                      title={
                        selectedDocument.status === "FAILED"
                          ? "Thử xử lý lại tài liệu"
                          : "Tạo lại chunks và embedding"
                      }
                      type="button"
                    >
                      {selectedDocument.status === "PROCESSING" ||
                      selectedDocument.status === "UPLOADED" ||
                      processingDocumentId === selectedDocument.id ? (
                        <LoaderCircle className="spin" size={15} />
                      ) : selectedDocument.status === "READY" ? (
                        <RotateCcw size={15} />
                      ) : (
                        <Play size={15} />
                      )}
                      {processingDocumentId === selectedDocument.id
                        ? "Đang gửi"
                        : selectedDocument.status === "UPLOADED"
                          ? "Đang chờ"
                          : selectedDocument.status === "PROCESSING"
                            ? "Đang xử lý"
                            : selectedDocument.status === "FAILED"
                              ? "Thử lại"
                              : "Xử lý lại"}
                    </button>
                  ) : null}
                </div>
              </div>

              <div className="document-facts">
                <span>Cập nhật {formatDate(selectedDocument.updated_at)}</span>
                <span>{selectedDocument.chunk_count} chunks</span>
                <span>{selectedDocument.uploaded_by_email}</span>
              </div>

              {selectedDocument.error_message ? (
                <div className="error-box">{selectedDocument.error_message}</div>
              ) : null}

              <div className="chunk-list">
                {loadingChunks ? (
                  <div className="loading-line">Đang tải chunk...</div>
                ) : chunks.length === 0 ? (
                  <div className="empty-panel">Tài liệu này chưa có chunk.</div>
                ) : (
                  chunks.slice(0, 80).map((chunk) => (
                    <article className="chunk-item" key={chunk.id}>
                      <header>
                        <span>Chunk {chunk.chunk_index}</span>
                        <span>
                          {chunk.page_number ? `Trang ${chunk.page_number}` : "Không rõ trang"}
                          {" · "}
                          {chunk.token_count} tokens
                          {" · "}
                          {chunk.has_embedding ? "Có vector" : "Chưa có vector"}
                        </span>
                      </header>
                      {chunk.section_title ? <strong>{chunk.section_title}</strong> : null}
                      <p>{chunk.content}</p>
                    </article>
                  ))
                )}
              </div>
            </>
          ) : (
            <div className="empty-panel">Chọn một tài liệu để xem chunks.</div>
          )}
        </div>
      </div>
    </section>
  );
}

function LoginScreen({
  onLogin
}: {
  onLogin: (auth: StoredAuth) => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const auth = await login(email, password);
      window.localStorage.setItem(AUTH_KEY, JSON.stringify(auth));
      onLogin(auth);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đăng nhập thất bại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <h1>Enterprise Knowledge RAG</h1>
        <p>Đăng nhập để hỏi đáp trên tài liệu bạn có quyền truy cập.</p>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              autoComplete="email"
              placeholder="admin@ou.edu.vn"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="password">Mật khẩu</label>
            <input
              id="password"
              autoComplete="current-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>
          {error ? <div className="error-box">{error}</div> : null}
          <button className="primary-button" disabled={loading} type="submit">
            {loading ? "Đang đăng nhập" : "Đăng nhập"}
          </button>
        </div>
      </form>
    </main>
  );
}

export default function Home() {
  const [auth, setAuth] = useState<StoredAuth | null>(null);
  const [activeView, setActiveView] = useState<"chat" | "documents">("chat");
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [documentChunks, setDocumentChunks] = useState<DocumentChunkItem[]>([]);
  const [documentSearch, setDocumentSearch] = useState("");
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [processingDocumentId, setProcessingDocumentId] = useState<number | null>(null);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const [documentError, setDocumentError] = useState("");
  const messageEndRef = useRef<HTMLDivElement | null>(null);

  const clearAuthState = useCallback(() => {
    window.localStorage.removeItem(AUTH_KEY);
    setAuth(null);
    setSessions([]);
    setMessages([]);
    setActiveSessionId(null);
    setDocuments([]);
    setSelectedDocumentId(null);
    setDocumentChunks([]);
    setDocumentSearch("");
  }, []);

  const logout = useCallback(async () => {
    try {
      if (auth) {
        await logoutSession(auth.access, auth.refresh);
      }
    } catch {
      // Local logout still completes if the access token has already expired.
    } finally {
      clearAuthState();
    }
  }, [auth, clearAuthState]);

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId),
    [activeSessionId, sessions]
  );
  const selectedDocument = useMemo(
    () => documents.find((document) => document.id === selectedDocumentId),
    [documents, selectedDocumentId]
  );
  const filteredDocuments = useMemo(() => {
    const query = documentSearch.trim().toLowerCase();

    if (!query) {
      return documents;
    }

    return documents.filter((document) =>
      [
        document.title,
        document.category_name || "",
        document.status,
        document.visibility,
        document.uploaded_by_email
      ]
        .join(" ")
        .toLowerCase()
        .includes(query)
    );
  }, [documentSearch, documents]);
  const readyDocumentCount = useMemo(
    () => documents.filter((document) => document.status === "READY").length,
    [documents]
  );
  const hasPendingDocuments = useMemo(
    () =>
      documents.some(
        (document) =>
          document.status === "UPLOADED" || document.status === "PROCESSING"
      ),
    [documents]
  );
  const canManageDocuments =
    auth?.user.role === "SYSTEM_ADMIN" || auth?.user.role === "ORG_ADMIN";

  useEffect(() => {
    setAuth(readStoredAuth());
  }, []);

  useEffect(() => {
    if (!auth) {
      return;
    }

    const token = auth.access;
    let cancelled = false;

    async function loadInitialSessions() {
      setLoadingSessions(true);
      setError("");

      try {
        const nextSessions = await fetchSessions(token);

        if (cancelled) {
          return;
        }

        setSessions(nextSessions);

        if (nextSessions.length > 0) {
          const session = await fetchSession(token, nextSessions[0].id);

          if (cancelled) {
            return;
          }

          setActiveSessionId(session.id);
          setMessages(session.messages || []);
          setSessions((current) =>
            current.map((item) =>
              item.id === session.id ? { ...item, ...session } : item
            )
          );
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Không tải được phiên chat."
          );
        }
      } finally {
        if (!cancelled) {
          setLoadingSessions(false);
        }
      }
    }

    void loadInitialSessions();

    return () => {
      cancelled = true;
    };
  }, [auth]);

  useEffect(() => {
    if (!auth) {
      return;
    }

    const expiresAt = accessTokenExpiresAt(auth.access);

    if (!expiresAt) {
      return;
    }

    const refreshBeforeExpiry = 60_000;
    const delay = Math.max(expiresAt - Date.now() - refreshBeforeExpiry, 0);
    const timer = window.setTimeout(async () => {
      try {
        const nextTokens = await refreshAccessToken(auth.refresh);
        const nextAuth = {
          ...auth,
          access: nextTokens.access,
          refresh: nextTokens.refresh || auth.refresh
        };

        window.localStorage.setItem(AUTH_KEY, JSON.stringify(nextAuth));
        setAuth(nextAuth);
      } catch {
        await logout();
      }
    }, delay);

    return () => window.clearTimeout(timer);
  }, [auth, logout]);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, asking]);

  useEffect(() => {
    if (!auth || activeView !== "documents" || !hasPendingDocuments) {
      return;
    }

    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const nextDocuments = await fetchDocuments(auth.access);

        if (cancelled) {
          return;
        }

        const sortedDocuments = [...nextDocuments].sort(
          (a, b) =>
            new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        );
        setDocuments(sortedDocuments);

        const nextSelected = sortedDocuments.find(
          (document) => document.id === selectedDocumentId
        );

        if (nextSelected?.status === "READY" && selectedDocument?.status !== "READY") {
          const chunks = await fetchDocumentChunks(auth.access, nextSelected.id);

          if (!cancelled) {
            setDocumentChunks(chunks);
          }
        }
      } catch {
        // Manual refresh still surfaces errors; polling remains quiet.
      }
    }, 2500);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [
    activeView,
    auth,
    hasPendingDocuments,
    selectedDocument?.status,
    selectedDocumentId
  ]);

  async function loadDocuments(token = auth?.access) {
    if (!token) {
      return;
    }

    setLoadingDocuments(true);
    setDocumentError("");

    try {
      const nextDocuments = await fetchDocuments(token);
      const sortedDocuments = [...nextDocuments].sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );

      setDocuments(sortedDocuments);

      const nextSelectedId =
        sortedDocuments.find((document) => document.id === selectedDocumentId)?.id ||
        sortedDocuments[0]?.id ||
        null;

      setSelectedDocumentId(nextSelectedId);

      if (nextSelectedId) {
        await openDocument(nextSelectedId, token);
      } else {
        setDocumentChunks([]);
      }
    } catch (err) {
      setDocumentError(
        err instanceof Error ? err.message : "Không tải được tài liệu."
      );
    } finally {
      setLoadingDocuments(false);
    }
  }

  async function openDocument(documentId: number, token = auth?.access) {
    if (!token) {
      return;
    }

    setSelectedDocumentId(documentId);
    setLoadingChunks(true);
    setDocumentError("");

    try {
      const chunks = await fetchDocumentChunks(token, documentId);
      setDocumentChunks(chunks);
    } catch (err) {
      setDocumentChunks([]);
      setDocumentError(
        err instanceof Error ? err.message : "Không tải được chunks."
      );
    } finally {
      setLoadingChunks(false);
    }
  }

  async function processDocument(documentId: number) {
    if (!auth || processingDocumentId !== null) {
      return;
    }

    setProcessingDocumentId(documentId);
    setDocumentError("");

    try {
      const queuedDocument = await queueDocumentProcessing(auth.access, documentId);
      setDocuments((current) =>
        current.map((document) =>
          document.id === queuedDocument.id ? queuedDocument : document
        )
      );
    } catch (err) {
      setDocumentError(
        err instanceof Error ? err.message : "Không thể đưa tài liệu vào hàng đợi."
      );
    } finally {
      setProcessingDocumentId(null);
    }
  }

  async function openSession(sessionId: number, token = auth?.access) {
    if (!token) {
      return;
    }

    setError("");
    setActiveView("chat");
    setActiveSessionId(sessionId);

    try {
      const session = await fetchSession(token, sessionId);
      setMessages(session.messages || []);
      setSessions((current) =>
        current.map((item) => (item.id === session.id ? { ...item, ...session } : item))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được hội thoại.");
    }
  }

  function startNewChat() {
    setActiveView("chat");
    setActiveSessionId(null);
    setMessages([]);
    setQuestion("");
    setError("");
  }

  async function submitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!auth || asking) {
      return;
    }

    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) {
      return;
    }

    const optimisticMessage: ChatMessage = {
      id: Date.now(),
      role: "USER",
      content: trimmedQuestion,
      metadata: {},
      created_at: new Date().toISOString()
    };

    setMessages((current) => [...current, optimisticMessage]);
    setQuestion("");
    setAsking(true);
    setError("");

    try {
      const response = await askQuestion(auth.access, {
        question: trimmedQuestion,
        session_id: activeSessionId || undefined,
        limit: 5
      });

      setActiveSessionId(response.session.id);
      setMessages((current) => [
        ...current.filter((message) => message.id !== optimisticMessage.id),
        response.user_message,
        response.assistant_message
      ]);
      setSessions((current) => {
        const exists = current.some((session) => session.id === response.session.id);
        const merged = exists
          ? current.map((session) =>
              session.id === response.session.id ? response.session : session
            )
          : [response.session, ...current];

        return merged.sort(
          (a, b) =>
            new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        );
      });
    } catch (err) {
      setMessages((current) =>
        current.filter((message) => message.id !== optimisticMessage.id)
      );
      setError(err instanceof Error ? err.message : "Không gửi được câu hỏi.");
    } finally {
      setAsking(false);
    }
  }

  if (!auth) {
    return <LoginScreen onLogin={setAuth} />;
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-title">
            <strong>Enterprise Knowledge RAG</strong>
            <span>
              {activeView === "chat"
                ? `${sessions.length} phiên chat`
                : `${readyDocumentCount}/${documents.length || 0} tài liệu sẵn sàng`}
            </span>
          </div>
          <button
            aria-label="Tạo phiên chat mới"
            className="icon-button"
            onClick={startNewChat}
            type="button"
          >
            <MessageSquarePlus size={18} />
          </button>
        </div>

        <div className="sidebar-tabs">
          <button
            className={activeView === "chat" ? "active" : ""}
            onClick={() => setActiveView("chat")}
            type="button"
          >
            <Bot size={16} />
            Chat
          </button>
          <button
            className={activeView === "documents" ? "active" : ""}
            onClick={() => {
              setActiveView("documents");
              void loadDocuments();
            }}
            type="button"
          >
            <FileText size={16} />
            Tài liệu
          </button>
        </div>

        {activeView === "chat" ? (
          <div className="session-list">
            {loadingSessions ? (
              <div className="loading-line">Đang tải...</div>
            ) : (
              sessions.map((session) => (
                <button
                  className={`session-item ${
                    session.id === activeSessionId ? "active" : ""
                  }`}
                  key={session.id}
                  onClick={() => void openSession(session.id)}
                  type="button"
                >
                  <strong>{session.title || `Chat #${session.id}`}</strong>
                  <span>{session.message_count} tin nhắn</span>
                </button>
              ))
            )}
          </div>
        ) : (
          <div className="sidebar-summary">
            <div>
              <span>Tài liệu truy cập được</span>
              <strong>{documents.length}</strong>
            </div>
            <div>
              <span>Sẵn sàng RAG</span>
              <strong>{readyDocumentCount}</strong>
            </div>
            <div>
              <span>Chunks đang chọn</span>
              <strong>{selectedDocument?.chunk_count || 0}</strong>
            </div>
          </div>
        )}

        <div className="sidebar-footer">
          <div className="user-line">
            <UserRound size={16} />
            <span>{auth.user.email}</span>
          </div>
          <button className="ghost-button" onClick={logout} type="button">
            <LogOut size={16} />
            Đăng xuất
          </button>
        </div>
      </aside>

      <section className="main">
        <header className="topbar">
          <div>
            <h1>
              {activeView === "documents"
                ? "Kho tài liệu"
                : activeSession?.title || "Chat tri thức nội bộ"}
            </h1>
            <p>
              {activeView === "documents"
                ? `${documents.length} tài liệu · ${readyDocumentCount} sẵn sàng`
                : auth.user.role}
            </p>
          </div>
          <div className="status-pill">
            {activeView === "documents" ? <FileText size={15} /> : <BookOpen size={15} />}
            {activeView === "documents" ? "Pipeline tài liệu" : "RBAC + Semantic Search"}
          </div>
        </header>

        {activeView === "chat" ? (
          <>
            <div className="messages">
              <div className="message-stack">
                {messages.length === 0 ? (
                  <div className="empty-state">
                    <div>
                      <Bot size={36} />
                      <strong>Đặt câu hỏi trên kho tài liệu</strong>
                      <span>
                        Ví dụ: học phí của khoa công nghệ thông tin năm học 2025
                      </span>
                    </div>
                  </div>
                ) : (
                  messages.map((message) => (
                    <ChatBubble key={message.id} message={message} />
                  ))
                )}
                {asking ? (
                  <div className="message-row assistant">
                    <article className="message">
                      <header className="message-header">
                        <span>RAG</span>
                        <span>Đang xử lý</span>
                      </header>
                      <div className="message-content">Đang tìm trong tài liệu...</div>
                    </article>
                  </div>
                ) : null}
                <div ref={messageEndRef} />
              </div>
            </div>

            <div className="composer-wrap">
              {error ? <div className="error-box">{error}</div> : null}
              <form className="composer" onSubmit={submitQuestion}>
                <textarea
                  aria-label="Câu hỏi"
                  onChange={(event) => setQuestion(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      event.currentTarget.form?.requestSubmit();
                    }
                  }}
                  placeholder="Nhập câu hỏi..."
                  value={question}
                />
                <button className="primary-button" disabled={asking} type="submit">
                  <Send size={16} />
                  Gửi
                </button>
              </form>
            </div>
          </>
        ) : (
          <DocumentManager
            canManageDocuments={canManageDocuments}
            chunks={documentChunks}
            documentError={documentError}
            documentSearch={documentSearch}
            documents={documents}
            filteredDocuments={filteredDocuments}
            loadingChunks={loadingChunks}
            loadingDocuments={loadingDocuments}
            processingDocumentId={processingDocumentId}
            onProcessDocument={(documentId) => void processDocument(documentId)}
            onRefresh={() => void loadDocuments()}
            onSearchChange={setDocumentSearch}
            onSelectDocument={(documentId) => void openDocument(documentId)}
            selectedDocument={selectedDocument}
          />
        )}
      </section>
    </main>
  );
}
