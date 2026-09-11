import {DocumentChunkItem, DocumentItem} from "@/lib/api";
import {ErrorBox} from "@/components/common/ErrorBox";
import {DocumentDetail} from "@/components/documents/DocumentDetail";
import {DocumentList} from "@/components/documents/DocumentList";
import {DocumentToolbar} from "@/components/documents/DocumentToolbar";

type DocumentManagerProps = {
  canManageDocuments: boolean;
  chunks: DocumentChunkItem[];
  documentError: string;
  documentSearch: string;
  documents: DocumentItem[];
  filteredDocuments: DocumentItem[];
  loadingChunks: boolean;
  loadingDocuments: boolean;
  onProcessDocument: (id: number) => Promise<void>;
  onRefresh: () => Promise<void>;
  onSearchChange: (value: string) => void;
  onSelectDocument: (id: number) => Promise<void>;
  processingDocumentId: number | null;
  readyCount: number;
  selectedDocument?: DocumentItem;
};

export function DocumentManager({
  canManageDocuments,
  chunks,
  documentError,
  documentSearch,
  documents,
  filteredDocuments,
  loadingChunks,
  loadingDocuments,
  onProcessDocument,
  onRefresh,
  onSearchChange,
  onSelectDocument,
  processingDocumentId,
  readyCount,
  selectedDocument
}: DocumentManagerProps) {
  const failedCount = documents.filter(
    (document) => document.status === "FAILED"
  ).length;
  const pendingCount = documents.filter(
    (document) =>
      document.status === "PROCESSING" || document.status === "UPLOADED"
  ).length;

  return (
    <section className="documents-view">
      <DocumentToolbar
        documentCount={documents.length}
        failedCount={failedCount}
        loading={loadingDocuments}
        onRefresh={onRefresh}
        onSearchChange={onSearchChange}
        pendingCount={pendingCount}
        readyCount={readyCount}
        search={documentSearch}
      />

      {documentError && !selectedDocument?.error_message ? (
        <ErrorBox message={documentError} />
      ) : null}

      <div className="documents-grid">
        <div className="document-list-panel">
          <DocumentList
            documents={filteredDocuments}
            loading={loadingDocuments}
            onSelect={onSelectDocument}
            selectedDocumentId={selectedDocument?.id || null}
          />
        </div>

        <div className="chunk-panel">
          <DocumentDetail
            canManageDocuments={canManageDocuments}
            chunks={chunks}
            document={selectedDocument}
            documentError={documentError}
            loadingChunks={loadingChunks}
            onProcess={onProcessDocument}
            processingDocumentId={processingDocumentId}
          />
        </div>
      </div>
    </section>
  );
}
