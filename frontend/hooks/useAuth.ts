import {useCallback, useEffect, useState} from "react";
import {login as loginRequest, logoutSession, refreshAccessToken, registerAccount} from "@/lib/api";
import {accessTokenExpiresAt, clearStoredAuth, readStoredAuth, writeStoredAuth} from "@/lib/auth-storage";
import {RegisterPayload} from "@/lib/api";
import {StoredAuth} from "@/types/auth";

export function useAuth() {
  const [auth, setAuth] = useState<StoredAuth | null>(null);
  const [loginError, setLoginError] = useState("");
  const [loginLoading, setLoginLoading] = useState(false);
  const [registerError, setRegisterError] = useState("");
  const [registerLoading, setRegisterLoading] = useState(false);

  useEffect(() => {
    setAuth(readStoredAuth());
  }, []);

  const clearAuthState = useCallback(() => {
    clearStoredAuth();
    setAuth(null);
  }, []);

  const logout = useCallback(async () => {
    try {
      if (auth) {
        await logoutSession(auth.access, auth.refresh);
      }
    } catch {
    } finally {
      clearAuthState();
    }
  }, [auth, clearAuthState]);

  const login = useCallback(async (email: string, password: string) => {
    setLoginError("");
    setLoginLoading(true);

    try {
      const nextAuth = await loginRequest(email, password);
      writeStoredAuth(nextAuth);
      setAuth(nextAuth);
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : "Đăng nhập thất bại.");
    } finally {
      setLoginLoading(false);
    }
  }, []);

  const register = useCallback(async (payload: RegisterPayload) => {
    setRegisterError("");
    setRegisterLoading(true);

    try {
      await registerAccount(payload);
      return true;
    } catch (error) {
      setRegisterError(error instanceof Error ? error.message : "Đăng ký thất bại.");
      return false;
    } finally {
      setRegisterLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!auth) {
      return;
    }

    const expiresAt = accessTokenExpiresAt(auth.access);

    if (!expiresAt) {
      return;
    }

    const refreshBeforeExpiry = 60_000;
    const delay = Math.max(expiresAt - Date.now() - refreshBeforeExpiry, 0);
    const timer = window.setTimeout(async () => {
      try {
        const nextTokens = await refreshAccessToken(auth.refresh);
        const nextAuth = {
          ...auth,
          access: nextTokens.access,
          refresh: nextTokens.refresh || auth.refresh
        };

        writeStoredAuth(nextAuth);
        setAuth(nextAuth);
      } catch {
        await logout();
      }
    }, delay);

    return () => window.clearTimeout(timer);
  }, [auth, logout]);

  return {
    auth,
    clearAuthState,
    login,
    loginError,
    loginLoading,
    logout,
    register,
    registerError,
    registerLoading,
  };
}
