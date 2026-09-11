import {LoaderCircle, Play, RotateCcw} from "lucide-react";
import {DocumentChunkItem, DocumentItem} from "@/lib/api";
import {ErrorBox} from "@/components/common/ErrorBox";
import {EmptyState} from "@/components/common/EmptyState";
import {ChunkList} from "@/components/documents/ChunkList";
import {StatusBadge} from "@/components/documents/StatusBadge";
import {formatDate, formatFileSize} from "@/lib/formatters";

type DocumentDetailProps = {
  canManageDocuments: boolean;
  chunks: DocumentChunkItem[];
  document?: DocumentItem;
  documentError: string;
  loadingChunks: boolean;
  onProcess: (id: number) => Promise<void>;
  processingDocumentId: number | null;
};

export function DocumentDetail({
  canManageDocuments,
  chunks,
  document,
  documentError,
  loadingChunks,
  onProcess,
  processingDocumentId
}: DocumentDetailProps) {
  if (!document) {
    return <EmptyState>Chọn một tài liệu để xem chunks.</EmptyState>;
  }

  const isBusy =
    document.status === "PROCESSING" ||
    document.status === "UPLOADED" ||
    processingDocumentId === document.id;

  return (
    <>
      <div className="document-detail">
        <div>
          <span className="eyebrow">Doc {document.id}</span>
          <h2>{document.title}</h2>
          <p>
            {document.category_name || "Chưa phân loại"} · {document.visibility} ·{" "}
            {formatFileSize(document.file_size)}
          </p>
        </div>

        <div className="document-detail-actions">
          <StatusBadge status={document.status} />
          {canManageDocuments && document.status !== "ARCHIVED" ? (
            <button
              className="text-button document-action"
              disabled={isBusy}
              onClick={() => void onProcess(document.id)}
              title={
                document.status === "FAILED"
                  ? "Thử xử lý lại tài liệu"
                  : "Tạo lại chunks và embedding"
              }
              type="button"
            >
              {isBusy ? (
                <LoaderCircle className="spin" size={15} />
              ) : document.status === "READY" ? (
                <RotateCcw size={15} />
              ) : (
                <Play size={15} />
              )}
              {processingDocumentId === document.id
                ? "Đang gửi"
                : document.status === "UPLOADED"
                  ? "Đang chờ"
                  : document.status === "PROCESSING"
                    ? "Đang xử lý"
                    : document.status === "FAILED"
                      ? "Thử lại"
                      : "Xử lý lại"}
            </button>
          ) : null}
        </div>
      </div>

      <div className="document-facts">
        <span>Cập nhật {formatDate(document.updated_at)}</span>
        <span>{document.chunk_count} chunks</span>
        <span>{document.uploaded_by_email}</span>
      </div>

      {document.error_message ? <ErrorBox message={document.error_message} /> : null}

      <div className="chunk-list">
        <ChunkList chunks={chunks} loading={loadingChunks} />
      </div>

      {documentError && !document.error_message ? (
        <ErrorBox message={documentError} />
      ) : null}
    </>
  );
}
