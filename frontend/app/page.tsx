"use client";

import {
  BookOpen,
  Bot,
  LogOut,
  MessageSquarePlus,
  Send,
  UserRound
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  askQuestion,
  ChatMessage,
  ChatSession,
  Citation,
  fetchSession,
  fetchSessions,
  login,
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

function formatTime(value: string) {
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit"
  }).format(new Date(value));
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

function LoginScreen({
  onLogin
}: {
  onLogin: (auth: StoredAuth) => void;
}) {
  const [email, setEmail] = useState("admin@ou.edu.vn");
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
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const messageEndRef = useRef<HTMLDivElement | null>(null);

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId),
    [activeSessionId, sessions]
  );

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
    messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, asking]);

  async function openSession(sessionId: number, token = auth?.access) {
    if (!token) {
      return;
    }

    setError("");
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
    setActiveSessionId(null);
    setMessages([]);
    setQuestion("");
    setError("");
  }

  function logout() {
    window.localStorage.removeItem(AUTH_KEY);
    setAuth(null);
    setSessions([]);
    setMessages([]);
    setActiveSessionId(null);
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
            <span>{sessions.length} phiên chat</span>
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
            <h1>{activeSession?.title || "Chat tri thức nội bộ"}</h1>
            <p>{auth.user.role}</p>
          </div>
          <div className="status-pill">
            <BookOpen size={15} />
            RBAC + Semantic Search
          </div>
        </header>

        <div className="messages">
          <div className="message-stack">
            {messages.length === 0 ? (
              <div className="empty-state">
                <div>
                  <Bot size={36} />
                  <strong>Đặt câu hỏi trên kho tài liệu</strong>
                  <span>Ví dụ: học phí của khoa công nghệ thông tin năm học 2025</span>
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
      </section>
    </main>
  );
}
