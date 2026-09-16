import {Bot, FileText, LogOut, MessageSquarePlus, Settings, UserRound} from "lucide-react";
import {ChatSession, DocumentItem} from "@/lib/api";
import {LoadingLine} from "@/components/common/LoadingLine";

type AppSidebarProps = {
  activeSessionId: number | null;
  activeView: "chat" | "documents" | "admin";
  canAccessAdmin: boolean;
  documents: DocumentItem[];
  loadingSessions: boolean;
  onLogout: () => Promise<void>;
  onNewChat: () => void;
  onOpenAdmin: () => void;
  onOpenDocuments: () => void;
  onOpenSession: (id: number) => Promise<void>;
  onSelectChat: () => void;
  readyDocumentCount: number;
  selectedDocument?: DocumentItem;
  sessions: ChatSession[];
  userEmail: string;
};

export function AppSidebar({
  activeSessionId,
  activeView,
  canAccessAdmin,
  documents,
  loadingSessions,
  onLogout,
  onNewChat,
  onOpenAdmin,
  onOpenDocuments,
  onOpenSession,
  onSelectChat,
  readyDocumentCount,
  selectedDocument,
  sessions,
  userEmail
}: AppSidebarProps) {
  return (
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
          onClick={onNewChat}
          type="button"
        >
          <MessageSquarePlus size={18} />
        </button>
      </div>

      <div className={`sidebar-tabs ${canAccessAdmin ? "admin-enabled" : ""}`}>
        <button
          className={activeView === "chat" ? "active" : ""}
          onClick={onSelectChat}
          type="button"
        >
          <Bot size={16} />
          Chat
        </button>
        <button
          className={activeView === "documents" ? "active" : ""}
          onClick={onOpenDocuments}
          type="button"
        >
          <FileText size={16} />
          Tài liệu
        </button>
        {canAccessAdmin ? (
          <button
            className={activeView === "admin" ? "active" : ""}
            onClick={onOpenAdmin}
            type="button"
          >
            <Settings size={16} />
            Admin
          </button>
        ) : null}
      </div>

      {activeView === "chat" ? (
        <div className="session-list">
          {loadingSessions ? (
            <LoadingLine>Đang tải...</LoadingLine>
          ) : (
            sessions.map((session) => (
              <button
                className={`session-item ${
                  session.id === activeSessionId ? "active" : ""
                }`}
                key={session.id}
                onClick={() => void onOpenSession(session.id)}
                type="button"
              >
                <strong>{session.title || `Chat #${session.id}`}</strong>
                <span>{session.message_count} tin nhắn</span>
              </button>
            ))
          )}
        </div>
      ) : activeView === "documents" ? (
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
      ) : (
        <div className="sidebar-summary">
          <div>
            <span>Phạm vi quản trị</span>
            <strong>Admin</strong>
          </div>
          <div>
            <span>Quyền truy cập</span>
            <strong>{canAccessAdmin ? "Đã cấp" : "Không có"}</strong>
          </div>
        </div>
      )}

      <div className="sidebar-footer">
        <div className="user-line">
          <UserRound size={16} />
          <span>{userEmail}</span>
        </div>
        <button className="ghost-button" onClick={() => void onLogout()} type="button">
          <LogOut size={16} />
          Đăng xuất
        </button>
      </div>
    </aside>
  );
}
