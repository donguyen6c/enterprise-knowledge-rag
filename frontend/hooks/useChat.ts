import {useCallback, useEffect, useMemo, useState} from "react";
import {askQuestion, ChatMessage, ChatSession, fetchSession, fetchSessions} from "@/lib/api";

export function useChat(token: string | null) {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [loadingSessions, setLoadingSessions] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId),
    [activeSessionId, sessions]
  );

  useEffect(() => {
    if (!token) {
      setSessions([]);
      setMessages([]);
      setActiveSessionId(null);
      return;
    }

    const accessToken = token;
    let cancelled = false;

    async function loadInitialSessions() {
      setLoadingSessions(true);
      setError("");

      try {
        const nextSessions = await fetchSessions(accessToken);

        if (cancelled) {
          return;
        }

        setSessions(nextSessions);

        if (nextSessions.length > 0) {
          const session = await fetchSession(accessToken, nextSessions[0].id);

          if (cancelled) {
            return;
          }

          setActiveSessionId(session.id);
          setMessages(session.messages || []);
          setSessions((current) =>
            current.map((item) =>
              item.id === session.id ? {...item, ...session} : item
            )
          );
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Không tải được phiên chat.");
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
  }, [token]);

  const openSession = useCallback(async (sessionId: number) => {
    if (!token) {
      return;
    }

    setError("");
    setActiveSessionId(sessionId);

    try {
      const session = await fetchSession(token, sessionId);
      setMessages(session.messages || []);
      setSessions((current) =>
        current.map((item) => (item.id === session.id ? {...item, ...session} : item))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Không tải được hội thoại.");
    }
  }, [token]);

  const startNewChat = useCallback(() => {
    setActiveSessionId(null);
    setMessages([]);
    setQuestion("");
    setError("");
  }, []);

  const submitQuestion = useCallback(async () => {
    if (!token || asking) {
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
      const response = await askQuestion(token, {
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
  }, [activeSessionId, asking, question, token]);

  return {activeSession, activeSessionId, asking, error, loadingSessions, messages, openSession, question, sessions, setQuestion, startNewChat, submitQuestion};
}
