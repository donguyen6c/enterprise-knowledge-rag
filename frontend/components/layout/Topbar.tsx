import {BookOpen, FileText, ShieldCheck} from "lucide-react";

type TopbarProps = {
  activeView: "chat" | "documents" | "admin";
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
  const isAdminView = activeView === "admin";

  return (
    <header className="topbar">
      <div>
        <h1>
          {isAdminView
            ? "Quản trị hệ thống"
            : isDocumentView
              ? "Kho tài liệu"
              : title || "Chat tri thức nội bộ"}
        </h1>
        <p>
          {isAdminView
            ? "System Admin / Organization Admin"
            : isDocumentView
            ? `${documentCount} tài liệu · ${readyDocumentCount} sẵn sàng`
            : role}
        </p>
      </div>
      <div className="status-pill">
        {isAdminView ? (
          <ShieldCheck size={15} />
        ) : isDocumentView ? (
          <FileText size={15} />
        ) : (
          <BookOpen size={15} />
        )}
        {isAdminView
          ? "Role-protected Admin"
          : isDocumentView
            ? "Pipeline tài liệu"
            : "RBAC + Semantic Search"}
      </div>
    </header>
  );
}
