import {RefreshCw, Search} from "lucide-react";

import {DocumentUploadForm} from "@/components/documents/DocumentUploadForm";
import {DocumentUploadPayload, Organization} from "@/lib/api";

type DocumentToolbarProps = {
  documentCount: number;
  canManageDocuments: boolean;
  failedCount: number;
  isSystemAdmin: boolean;
  loading: boolean;
  onRefresh: () => Promise<void>;
  onSearchChange: (value: string) => void;
  onUpload: (payload: DocumentUploadPayload) => Promise<boolean>;
  organizations: Organization[];
  pendingCount: number;
  readyCount: number;
  search: string;
  uploading: boolean;
};

export function DocumentToolbar({
  documentCount,
  canManageDocuments,
  failedCount,
  isSystemAdmin,
  loading,
  onRefresh,
  onSearchChange,
  onUpload,
  organizations,
  pendingCount,
  readyCount,
  search,
  uploading
}: DocumentToolbarProps) {
  return (
    <div className="documents-toolbar">
      <div className="document-metrics" aria-label="Thống kê tài liệu">
        <span>{documentCount} tài liệu</span>
        <span>{readyCount} sẵn sàng</span>
        <span>{failedCount} lỗi</span>
        <span>{pendingCount} chờ xử lý</span>
      </div>

      <label className="document-search">
        <Search size={16} />
        <input
          aria-label="Tìm tài liệu"
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder="Tìm theo tên, loại, trạng thái..."
          value={search}
        />
      </label>

      <button
        className="icon-button light"
        disabled={loading}
        onClick={() => void onRefresh()}
        title="Tải lại tài liệu"
        type="button"
      >
        <RefreshCw size={17} />
      </button>

      {canManageDocuments ? (
        <DocumentUploadForm
          isSystemAdmin={isSystemAdmin}
          onUpload={onUpload}
          organizations={organizations}
          uploading={uploading}
        />
      ) : null}
    </div>
  );
}
