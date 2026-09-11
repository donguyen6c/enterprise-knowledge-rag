"use client";

import {useState} from "react";

import {LoginScreen} from "@/components/auth/LoginScreen";
import {ChatView} from "@/components/chat/ChatView";
import {DocumentManager} from "@/components/documents/DocumentManager";
import {AppSidebar} from "@/components/layout/AppSidebar";
import {Topbar} from "@/components/layout/Topbar";
import {useAuth} from "@/hooks/useAuth";
import {useChat} from "@/hooks/useChat";
import {useDocuments} from "@/hooks/useDocuments";

type ActiveView = "chat" | "documents";

export default function Home() {
  const [activeView, setActiveView] = useState<ActiveView>("chat");
  const {auth, login, loginError, loginLoading, logout} = useAuth();
  const chat = useChat(auth?.access || null);
  const documents = useDocuments(auth?.access || null, activeView);

  if (!auth) {
    return (
      <LoginScreen
        error={loginError}
        loading={loginLoading}
        onLogin={login}
      />
    );
  }

  const canManageDocuments =
    auth.user.role === "SYSTEM_ADMIN" || auth.user.role === "ORG_ADMIN";

  function openDocuments() {
    setActiveView("documents");
    void documents.loadDocuments();
  }

  function openNewChat() {
    setActiveView("chat");
    chat.startNewChat();
  }

  async function openSession(sessionId: number) {
    setActiveView("chat");
    await chat.openSession(sessionId);
  }

  return (
    <main className="app-shell">
      <AppSidebar
        activeSessionId={chat.activeSessionId}
        activeView={activeView}
        documents={documents.documents}
        loadingSessions={chat.loadingSessions}
        onLogout={logout}
        onNewChat={openNewChat}
        onOpenDocuments={openDocuments}
        onOpenSession={openSession}
        onSelectChat={() => setActiveView("chat")}
        readyDocumentCount={documents.readyDocumentCount}
        selectedDocument={documents.selectedDocument}
        sessions={chat.sessions}
        userEmail={auth.user.email}
      />

      <section className="main">
        <Topbar
          activeView={activeView}
          documentCount={documents.documents.length}
          readyDocumentCount={documents.readyDocumentCount}
          role={auth.user.role}
          title={chat.activeSession?.title}
        />

        {activeView === "chat" ? (
          <ChatView
            asking={chat.asking}
            error={chat.error}
            messages={chat.messages}
            onQuestionChange={chat.setQuestion}
            onSubmit={chat.submitQuestion}
            question={chat.question}
          />
        ) : (
          <DocumentManager
            canManageDocuments={canManageDocuments}
            chunks={documents.documentChunks}
            documentError={documents.documentError}
            documentSearch={documents.documentSearch}
            documents={documents.documents}
            filteredDocuments={documents.filteredDocuments}
            loadingChunks={documents.loadingChunks}
            loadingDocuments={documents.loadingDocuments}
            onProcessDocument={documents.processDocument}
            onRefresh={documents.loadDocuments}
            onSearchChange={documents.setDocumentSearch}
            onSelectDocument={documents.openDocument}
            processingDocumentId={documents.processingDocumentId}
            readyCount={documents.readyDocumentCount}
            selectedDocument={documents.selectedDocument}
          />
        )}
      </section>
    </main>
  );
}
