import {ChatMessage} from "@/lib/api";
import {CitationList} from "@/components/chat/CitationList";
import {formatTime} from "@/lib/formatters";

type ChatBubbleProps = {
  message: ChatMessage;
};

export function ChatBubble({message}: ChatBubbleProps) {
  const isUser = message.role === "USER";

  return (
    <div className={`message-row ${isUser ? "user" : "assistant"}`}>
      <article className="message">
        <header className="message-header">
          <span>{isUser ? "Bạn" : "RAG"}</span>
          <span>{formatTime(message.created_at)}</span>
        </header>
        <div className="message-content">{message.content}</div>
        {!isUser ? <CitationList citations={message.metadata?.citations} /> : null}
      </article>
    </div>
  );
}
