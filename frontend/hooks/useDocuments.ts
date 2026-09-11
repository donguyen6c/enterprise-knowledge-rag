import {useCallback, useEffect, useMemo, useState} from "react";
import {
  DocumentChunkItem,
  DocumentItem,
  fetchDocumentChunks,
  fetchDocuments,
  queueDocumentProcessing
} from "@/lib/api";

export function useDocuments(token: string | null, activeView: "chat" | "documents") {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null);
  const [documentChunks, setDocumentChunks] = useState<DocumentChunkItem[]>([]);
  const [documentSearch, setDocumentSearch] = useState("");
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [processingDocumentId, setProcessingDocumentId] = useState<number | null>(null);
  const [documentError, setDocumentError] = useState("");

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
    filteredDocuments,
    hasPendingDocuments,
    loadingChunks,
    loadingDocuments,
    loadDocuments,
    openDocument,
    processDocument,
    processingDocumentId,
    readyDocumentCount,
    selectedDocument,
    selectedDocumentId,
    setDocumentSearch
  };
}
