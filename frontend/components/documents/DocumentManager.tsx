import {
  DocumentChunkItem,
  DocumentItem,
  DocumentUploadPayload,
  Organization
} from "@/lib/api";
import {ErrorBox} from "@/components/common/ErrorBox";
import {DocumentDetail} from "@/components/documents/DocumentDetail";
import {DocumentList} from "@/components/documents/DocumentList";
import {DocumentToolbar} from "@/components/documents/DocumentToolbar";

type DocumentManagerProps = {
  canManageDocuments: boolean;
  downloadingDocumentId: number | null;
  chunks: DocumentChunkItem[];
  documentError: string;
  documentSearch: string;
  documents: DocumentItem[];
  filteredDocuments: DocumentItem[];
  loadingChunks: boolean;
  loadingDocuments: boolean;
  isSystemAdmin: boolean;
  onProcessDocument: (id: number) => Promise<void>;
  onDownloadDocument: (document: DocumentItem) => Promise<void>;
  onRefresh: () => Promise<void>;
  onSearchChange: (value: string) => void;
  onSelectDocument: (id: number) => Promise<void>;
  onUploadDocument: (payload: DocumentUploadPayload) => Promise<boolean>;
  organizations: Organization[];
  processingDocumentId: number | null;
  readyCount: number;
  selectedDocument?: DocumentItem;
  uploadingDocument: boolean;
};

export function DocumentManager({
  canManageDocuments,
  downloadingDocumentId,
  chunks,
  documentError,
  documentSearch,
  documents,
  filteredDocuments,
  loadingChunks,
  loadingDocuments,
  isSystemAdmin,
  onDownloadDocument,
  onProcessDocument,
  onRefresh,
  onSearchChange,
  onSelectDocument,
  onUploadDocument,
  organizations,
  processingDocumentId,
  readyCount,
  selectedDocument,
  uploadingDocument
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
        canManageDocuments={canManageDocuments}
        documentCount={documents.length}
        failedCount={failedCount}
        isSystemAdmin={isSystemAdmin}
        loading={loadingDocuments}
        onRefresh={onRefresh}
        onSearchChange={onSearchChange}
        onUpload={onUploadDocument}
        organizations={organizations}
        pendingCount={pendingCount}
        readyCount={readyCount}
        search={documentSearch}
        uploading={uploadingDocument}
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
            downloadingDocumentId={downloadingDocumentId}
            loadingChunks={loadingChunks}
            onDownload={onDownloadDocument}
            onProcess={onProcessDocument}
            processingDocumentId={processingDocumentId}
          />
        </div>
      </div>
    </section>
  );
}
