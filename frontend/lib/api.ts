/**
 * apiFetch — drop-in replacement for fetch() that automatically attaches
 * the API key stored in sessionStorage as an Authorization: Bearer header.
 *
 * Usage:
 *   import { apiFetch } from "@/lib/api";
 *   const res = await apiFetch("/api/sources?company_code=DEVES");
 *   const data = await res.json();
 */

/**
 * Base URL for backend API calls.
 *
 * - Production / Docker: set NEXT_PUBLIC_API_BASE_URL to the backend origin
 *   (e.g. "https://api.example.com"). The browser will call that URL directly.
 *
 * - Local dev (default): leave NEXT_PUBLIC_API_BASE_URL unset or empty.
 *   API_BASE is then "" so every call becomes a relative path (/api/…).
 *   next.config.mjs rewrites proxy those relative paths to localhost:8080
 *   server-side, so the browser never needs to reach port 8080 directly.
 *
 * NOTE: We use ?? (nullish coalescing) not || so that an explicit empty
 * string in .env.local is respected rather than falling back to localhost.
 */
export const API_BASE: string =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE_URL != null
    ? process.env.NEXT_PUBLIC_API_BASE_URL
    : undefined) ?? "";

export const TOKEN_KEY = "llm_wiki_api_key";

export function getToken(): string {
  if (typeof window === "undefined") return "";
  return sessionStorage.getItem(TOKEN_KEY) ?? "";
}

export function setToken(key: string): void {
  sessionStorage.setItem(TOKEN_KEY, key);
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

export function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const token = getToken();
  const headers = new Headers(init?.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return fetch(input, { ...init, headers });
}
