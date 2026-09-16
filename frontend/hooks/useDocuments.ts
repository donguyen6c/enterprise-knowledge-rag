import {useCallback, useEffect, useMemo, useState} from "react";
import {
  DocumentChunkItem,
  DocumentItem,
  DocumentUploadPayload,
  downloadDocument,
  fetchActiveOrganizations,
  fetchDocumentChunks,
  fetchDocuments,
  Organization,
  queueDocumentProcessing,
  uploadDocument
} from "@/lib/api";

export function useDocuments(
  token: string | null,
  activeView: "chat" | "documents" | "admin",
  role?: string
) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [documentChunks, setDocumentChunks] = useState<DocumentChunkItem[]>([]);
  const [documentSearch, setDocumentSearch] = useState("");
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [processingDocumentId, setProcessingDocumentId] = useState<number | null>(null);
  const [documentError, setDocumentError] = useState("");
  const [availableOrganizations, setAvailableOrganizations] = useState<Organization[]>([]);
  const [uploadingDocument, setUploadingDocument] = useState(false);
  const [downloadingDocumentId, setDownloadingDocumentId] = useState<number | null>(null);

  const selectedDocument = useMemo(
    () => documents.find((document) => document.id === selectedDocumentId),
    [documents, selectedDocumentId]
  );
  const filteredDocuments = useMemo(() => {
    const query = documentSearch.trim().toLowerCase();

    if (!query) {
      return documents;
    }

    return documents.filter((document) =>
      [
        document.title,
        document.category_name || "",
        document.status,
        document.visibility,
        document.uploaded_by_email
      ]
        .join(" ")
        .toLowerCase()
        .includes(query)
    );
  }, [documentSearch, documents]);
  const readyDocumentCount = useMemo(
    () => documents.filter((document) => document.status === "READY").length,
    [documents]
  );
  const hasPendingDocuments = useMemo(
    () => documents.some(
      (document) => document.status === "UPLOADED" || document.status === "PROCESSING"
    ),
    [documents]
  );

  const openDocument = useCallback(async (documentId: number) => {
    if (!token) {
      return;
    }

    setSelectedDocumentId(documentId);
    setLoadingChunks(true);
    setDocumentError("");

    try {
      const chunks = await fetchDocumentChunks(token, documentId);
      setDocumentChunks(chunks);
    } catch (err) {
      setDocumentChunks([]);
      setDocumentError(err instanceof Error ? err.message : "Không tải được chunks.");
    } finally {
      setLoadingChunks(false);
    }
  }, [token]);

  const loadDocuments = useCallback(async () => {
    if (!token) {
      return;
    }

    setLoadingDocuments(true);
    setDocumentError("");

    try {
      const nextDocuments = await fetchDocuments(token);
      const sortedDocuments = [...nextDocuments].sort(
        (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );

      setDocuments(sortedDocuments);

      const nextSelectedId =
        sortedDocuments.find((document) => document.id === selectedDocumentId)?.id ||
        sortedDocuments[0]?.id ||
        null;

      setSelectedDocumentId(nextSelectedId);

      if (nextSelectedId) {
        await openDocument(nextSelectedId);
      } else {
        setDocumentChunks([]);
      }
    } catch (err) {
      setDocumentError(err instanceof Error ? err.message : "Không tải được tài liệu.");
    } finally {
      setLoadingDocuments(false);
    }
  }, [openDocument, selectedDocumentId, token]);

  const processDocument = useCallback(async (documentId: number) => {
    if (!token || processingDocumentId !== null) {
      return;
    }

    setProcessingDocumentId(documentId);
    setDocumentError("");

    try {
      const queuedDocument = await queueDocumentProcessing(token, documentId);
      setDocuments((current) =>
        current.map((document) =>
          document.id === queuedDocument.id ? queuedDocument : document
        )
      );
    } catch (err) {
      setDocumentError(
        err instanceof Error ? err.message : "Không thể đưa tài liệu vào hàng đợi."
      );
    } finally {
      setProcessingDocumentId(null);
    }
  }, [processingDocumentId, token]);

  const loadAvailableOrganizations = useCallback(async () => {
    if (role !== "SYSTEM_ADMIN") {
      setAvailableOrganizations([]);
      return;
    }

    try {
      setAvailableOrganizations(await fetchActiveOrganizations());
    } catch {
      // Uploading will surface a useful error if the organization list is unavailable.
    }
  }, [role]);

  const uploadNewDocument = useCallback(
    async (payload: DocumentUploadPayload) => {
      if (!token || uploadingDocument) {
        return false;
      }

      setUploadingDocument(true);
      setDocumentError("");

      try {
        const document = await uploadDocument(token, payload);
        setDocuments((current) => [document, ...current]);
        setSelectedDocumentId(document.id);
        setDocumentChunks([]);
        return true;
      } catch (error) {
        setDocumentError(
          error instanceof Error ? error.message : "Không thể tải tài liệu lên."
        );
        return false;
      } finally {
        setUploadingDocument(false);
      }
    },
    [token, uploadingDocument]
  );

  const downloadSelectedDocument = useCallback(
    async (document: DocumentItem) => {
      if (!token || downloadingDocumentId !== null) {
        return;
      }

      setDownloadingDocumentId(document.id);
      setDocumentError("");

      try {
        const file = await downloadDocument(token, document.id);
        const objectUrl = window.URL.createObjectURL(file);
        const anchor = window.document.createElement("a");
        anchor.href = objectUrl;
        anchor.download = document.original_filename || document.title;
        anchor.click();
        window.URL.revokeObjectURL(objectUrl);
      } catch (error) {
        setDocumentError(
          error instanceof Error ? error.message : "Không thể tải tài liệu xuống."
        );
      } finally {
        setDownloadingDocumentId(null);
      }
    },
    [downloadingDocumentId, token]
  );

  useEffect(() => {
    if (activeView === "documents") {
      void loadAvailableOrganizations();
    }
  }, [activeView, loadAvailableOrganizations]);

  useEffect(() => {
    if (!token || activeView !== "documents" || !hasPendingDocuments) {
      return;
    }

    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const nextDocuments = await fetchDocuments(token);

        if (cancelled) {
          return;
        }

        const sortedDocuments = [...nextDocuments].sort(
          (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
        );
        setDocuments(sortedDocuments);

        const nextSelected = sortedDocuments.find(
          (document) => document.id === selectedDocumentId
        );

        if (nextSelected?.status === "READY" && selectedDocument?.status !== "READY") {
          const chunks = await fetchDocumentChunks(token, nextSelected.id);

          if (!cancelled) {
            setDocumentChunks(chunks);
          }
        }
      } catch {
        // Manual refresh still surfaces errors; polling remains quiet.
      }
    }, 2500);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [activeView, hasPendingDocuments, selectedDocument?.status, selectedDocumentId, token]);

  return {
    documentChunks,
    documentError,
    documentSearch,
    documents,
    availableOrganizations,
    downloadingDocumentId,
    filteredDocuments,
    hasPendingDocuments,
    loadingChunks,
    loadingDocuments,
    loadDocuments,
    downloadSelectedDocument,
    openDocument,
    processDocument,
    processingDocumentId,
    readyDocumentCount,
    selectedDocument,
    selectedDocumentId,
    setDocumentSearch,
    uploadNewDocument,
    uploadingDocument
  };
}
