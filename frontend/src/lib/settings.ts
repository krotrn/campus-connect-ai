/**
 * Browser-side settings.
 *
 * By default the console talks to its own Next route handlers (`/api/aeia/*`),
 * which hold the backend API key server-side. Nothing secret is stored here in
 * that mode.
 *
 * Advanced users can point the console at their own AEIA deployment. Because
 * proxying to an arbitrary user-supplied URL would turn this app into an open
 * proxy, a custom backend is called directly from the browser instead — which
 * means the user must also supply the key for *their* backend. That key is
 * theirs, not ours, and is only ever sent to the host they entered.
 */

const BACKEND_URL_KEY = "aeia_backend_url";
const API_KEY_KEY = "aeia_api_key";
const GEMINI_API_KEY_KEY = "aeia_gemini_api_key";

/** Same-origin proxy routes used when no custom backend is configured. */
export const PROXY_ROUTES = {
  health: "/api/aeia/health",
  askStream: "/api/aeia/ask/stream",
  agent: "/api/aeia/agent",
} as const;

function readLocal(key: string): string {
  if (typeof window === "undefined") return "";
  try {
    return localStorage.getItem(key)?.trim() ?? "";
  } catch {
    // Private browsing or blocked site data.
    return "";
  }
}

function writeLocal(key: string, value: string): void {
  if (typeof window === "undefined") return;
  try {
    const trimmed = value.trim();
    if (trimmed) {
      localStorage.setItem(key, trimmed);
    } else {
      localStorage.removeItem(key);
    }
  } catch {
    // Ignore: settings are a convenience, not a requirement.
  }
}

/** A user-supplied backend URL, or "" when using the built-in proxy. */
export function getCustomBackendUrl(): string {
  return readLocal(BACKEND_URL_KEY).replace(/\/+$/, "");
}

export function setCustomBackendUrl(url: string): void {
  writeLocal(BACKEND_URL_KEY, url.replace(/\/+$/, ""));
}

/** The API key for a user-supplied backend. Unused in default proxy mode. */
export function getCustomApiKey(): string {
  return readLocal(API_KEY_KEY);
}

export function setCustomApiKey(key: string): void {
  writeLocal(API_KEY_KEY, key);
}

export function getStoredGeminiApiKey(): string {
  return readLocal(GEMINI_API_KEY_KEY);
}

export function setStoredGeminiApiKey(key: string): void {
  writeLocal(GEMINI_API_KEY_KEY, key);
}

export function isUsingCustomBackend(): boolean {
  return getCustomBackendUrl().length > 0;
}

/**
 * Resolve the endpoint and headers for a backend call.
 *
 * Default: same-origin proxy route, no credentials in the browser.
 * Custom backend: direct call carrying the user's own key.
 */
export function resolveEndpoint(route: keyof typeof PROXY_ROUTES): {
  url: string;
  headers: Record<string, string>;
  direct: boolean;
} {
  const headers: Record<string, string> = { "Content-Type": "application/json" };

  const geminiKey = getStoredGeminiApiKey();
  if (geminiKey) {
    headers["X-Gemini-API-Key"] = geminiKey;
  }

  const custom = getCustomBackendUrl();
  if (!custom) {
    return { url: PROXY_ROUTES[route], headers, direct: false };
  }

  const paths: Record<keyof typeof PROXY_ROUTES, string> = {
    health: "/health",
    askStream: "/ask/stream",
    agent: "/agent/ask",
  };

  const apiKey = getCustomApiKey();
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  return { url: `${custom}${paths[route]}`, headers, direct: true };
}
