"use client";

import {useState} from "react";

import {LoginScreen} from "@/components/auth/LoginScreen";
import {AdminDashboard} from "@/components/admin/AdminDashboard";
import {RegisterScreen} from "@/components/auth/RegisterScreen";
import {ChatView} from "@/components/chat/ChatView";
import {DocumentManager} from "@/components/documents/DocumentManager";
import {AppSidebar} from "@/components/layout/AppSidebar";
import {Topbar} from "@/components/layout/Topbar";
import {useAuth} from "@/hooks/useAuth";
import {useAdmin} from "@/hooks/useAdmin";
import {useChat} from "@/hooks/useChat";
import {useDocuments} from "@/hooks/useDocuments";

type ActiveView = "chat" | "documents" | "admin";

export default function Home() {
  const [activeView, setActiveView] = useState<ActiveView>("chat");
  const [authView, setAuthView] = useState<"login" | "register">("login");
  const [registerSuccessMessage, setRegisterSuccessMessage] = useState("");
  const {auth, login, loginError, loginLoading, logout, register, registerError, registerLoading} = useAuth();
  const chat = useChat(auth?.access || null);
  const documents = useDocuments(auth?.access || null, activeView, auth?.user.role);
  const admin = useAdmin(auth?.access || null, auth?.user.role, activeView);

  if (!auth) {
    if (authView === "register") {
      return (
        <RegisterScreen
          error={registerError}
          loading={registerLoading}
          onRegister={async (payload) => {
            const succeeded = await register(payload);
            if (succeeded) {
              setRegisterSuccessMessage("Đăng ký tài khoản thành công. Bạn có thể đăng nhập ngay.");
              setAuthView("login");
            }
          }}
          onSwitchToLogin={() => {
            setAuthView("login");
          }}
        />
      );
    }

    return (
      <LoginScreen
        error={loginError}
        loading={loginLoading}
        onLogin={login}
        onSwitchToRegister={() => {
          setAuthView("register");
        }}
        successMessage={registerSuccessMessage}
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

  function openAdmin() {
    if (admin.canAccessAdmin) {
      setActiveView("admin");
    }
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
        canAccessAdmin={admin.canAccessAdmin}
        documents={documents.documents}
        loadingSessions={chat.loadingSessions}
        onLogout={logout}
        onNewChat={openNewChat}
        onOpenAdmin={openAdmin}
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
        ) : activeView === "documents" ? (
          <DocumentManager
            canManageDocuments={canManageDocuments}
            chunks={documents.documentChunks}
            documentError={documents.documentError}
            documentSearch={documents.documentSearch}
            downloadingDocumentId={documents.downloadingDocumentId}
            documents={documents.documents}
            filteredDocuments={documents.filteredDocuments}
            loadingChunks={documents.loadingChunks}
            loadingDocuments={documents.loadingDocuments}
            isSystemAdmin={auth.user.role === "SYSTEM_ADMIN"}
            onDownloadDocument={documents.downloadSelectedDocument}
            onProcessDocument={documents.processDocument}
            onRefresh={documents.loadDocuments}
            onSearchChange={documents.setDocumentSearch}
            onSelectDocument={documents.openDocument}
            onUploadDocument={documents.uploadNewDocument}
            organizations={documents.availableOrganizations}
            processingDocumentId={documents.processingDocumentId}
            readyCount={documents.readyDocumentCount}
            selectedDocument={documents.selectedDocument}
            uploadingDocument={documents.uploadingDocument}
          />
        ) : (
          <AdminDashboard
            currentUserId={auth.user.id}
            error={admin.error}
            isSystemAdmin={admin.isSystemAdmin}
            loading={admin.loading}
            onCreateOrganization={admin.createOrganization}
            onCreateUser={admin.createUser}
            onRefresh={admin.loadAdminData}
            onToggleOrganizationActive={admin.toggleOrganizationActive}
            onToggleUserActive={admin.toggleUserActive}
            onUpdateUserRole={admin.updateUserRole}
            organizations={admin.organizations}
            saving={admin.saving}
            users={admin.users}
          />
        )}
      </section>
    </main>
  );
}
