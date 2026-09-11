import {useEffect, useRef} from "react";
import {Bot} from "lucide-react";
import {ChatMessage} from "@/lib/api";
import {ChatBubble} from "@/components/chat/ChatBubble";
import {ChatComposer} from "@/components/chat/ChatComposer";

type ChatViewProps = {
  asking: boolean;
  error: string;
  messages: ChatMessage[];
  onQuestionChange: (value: string) => void;
  onSubmit: () => Promise<void>;
  question: string;
};

export function ChatView({
  asking,
  error,
  messages,
  onQuestionChange,
  onSubmit,
  question
}: ChatViewProps) {
  const messageEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messageEndRef.current?.scrollIntoView({behavior: "smooth"});
  }, [asking, messages]);

  return (
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
                <div className="message-content">
                  Đang tìm trong tài liệu...
                </div>
              </article>
            </div>
          ) : null}

          <div ref={messageEndRef} />
        </div>
      </div>

      <ChatComposer
        asking={asking}
        error={error}
        onQuestionChange={onQuestionChange}
        onSubmit={onSubmit}
        question={question}
      />
    </>
  );
}
