import {FormEvent, KeyboardEvent} from "react";
import {Send} from "lucide-react";
import {ErrorBox} from "@/components/common/ErrorBox";

type ChatComposerProps = {
  asking: boolean;
  error: string;
  onQuestionChange: (value: string) => void;
  onSubmit: () => Promise<void>;
  question: string;
};

export function ChatComposer({asking,
  error,
  onQuestionChange,
  onSubmit,
  question
}: ChatComposerProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSubmit();
  }

  return (
    <div className="composer-wrap">
      {error ? <ErrorBox message={error} /> : null}
      <form className="composer" onSubmit={submit}>
        <textarea
          aria-label="Câu hỏi"
          onChange={(event) => onQuestionChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Nhập câu hỏi..."
          value={question}
        />
        <button className="primary-button" disabled={asking} type="submit">
          <Send size={16} />
          Gửi
        </button>
      </form>
    </div>
  );
}
