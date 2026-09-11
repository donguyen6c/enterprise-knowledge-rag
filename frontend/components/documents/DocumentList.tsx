import {DocumentItem} from "@/lib/api";
import {EmptyState} from "@/components/common/EmptyState";
import {LoadingLine} from "@/components/common/LoadingLine";
import {StatusBadge} from "@/components/documents/StatusBadge";

type DocumentListProps = {
  documents: DocumentItem[];
  loading: boolean;
  onSelect: (id: number) => Promise<void>;
  selectedDocumentId: number | null;
};

export function DocumentList({
  documents,
  loading,
  onSelect,
  selectedDocumentId
}: DocumentListProps) {
  if (loading) {
    return <LoadingLine>Đang tải tài liệu...</LoadingLine>;
  }

  if (documents.length === 0) {
    return <EmptyState>Không có tài liệu phù hợp.</EmptyState>;
  }

  return (
    <>
      {documents.map((document) => (
        <button
          className={`document-row ${
            document.id === selectedDocumentId ? "active" : ""
          }`}
          key={document.id}
          onClick={() => void onSelect(document.id)}
          type="button"
        >
          <div>
            <strong>{document.title}</strong>
            <span>
              Doc {document.id} · {document.category_name || "Chưa phân loại"}
            </span>
          </div>
          <div className="document-row-meta">
            <StatusBadge status={document.status} />
            <span>{document.chunk_count} chunks</span>
          </div>
        </button>
      ))}
    </>
  );
}
