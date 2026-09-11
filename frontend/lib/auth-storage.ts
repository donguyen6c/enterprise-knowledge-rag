import {StoredAuth} from "@/types/auth";

export const AUTH_KEY = "ekr.auth";

export function readStoredAuth(): StoredAuth | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.localStorage.getItem(AUTH_KEY);

  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as StoredAuth;
  } catch {
    window.localStorage.removeItem(AUTH_KEY);
    return null;
  }
}

export function writeStoredAuth(auth: StoredAuth) {
  window.localStorage.setItem(AUTH_KEY, JSON.stringify(auth));
}

export function clearStoredAuth() {
  window.localStorage.removeItem(AUTH_KEY);
}

export function accessTokenExpiresAt(token: string): number | null {
  try {
    const payload = token.split(".")[1];
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    const decoded = JSON.parse(window.atob(padded)) as {exp?: number};

    return decoded.exp ? decoded.exp * 1000 : null;
  } catch {
    return null;
  }
}
