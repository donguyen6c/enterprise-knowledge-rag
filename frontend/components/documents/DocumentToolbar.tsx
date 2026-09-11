import {RefreshCw, Search} from "lucide-react";

type DocumentToolbarProps = {
  documentCount: number;
  failedCount: number;
  loading: boolean;
  onRefresh: () => Promise<void>;
  onSearchChange: (value: string) => void;
  pendingCount: number;
  readyCount: number;
  search: string;
};

export function DocumentToolbar({
  documentCount,
  failedCount,
  loading,
  onRefresh,
  onSearchChange,
  pendingCount,
  readyCount,
  search
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
    </div>
  );
}
