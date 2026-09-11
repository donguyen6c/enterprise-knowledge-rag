import {BookOpen, FileText} from "lucide-react";

type TopbarProps = {
  activeView: "chat" | "documents";
  documentCount: number;
  readyDocumentCount: number;
  role: string;
  title?: string;
};

export function Topbar({
  activeView,
  documentCount,
  readyDocumentCount,
  role,
  title
}: TopbarProps) {
  const isDocumentView = activeView === "documents";

  return (
    <header className="topbar">
      <div>
        <h1>
          {isDocumentView ? "Kho tài liệu" : title || "Chat tri thức nội bộ"}
        </h1>
        <p>
          {isDocumentView
            ? `${documentCount} tài liệu · ${readyDocumentCount} sẵn sàng`
            : role}
        </p>
      </div>
      <div className="status-pill">
        {isDocumentView ? <FileText size={15} /> : <BookOpen size={15} />}
        {isDocumentView ? "Pipeline tài liệu" : "RBAC + Semantic Search"}
      </div>
    </header>
  );
}
