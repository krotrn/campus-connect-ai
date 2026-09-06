import { env } from "@/config/env";

const BACKEND_URL_KEY = "aeia_backend_url";
const API_KEY_KEY = "aeia_api_key";

export function getStoredBackendUrl(): string {
  if (typeof window === "undefined") {
    return env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  }
  const stored = localStorage.getItem(BACKEND_URL_KEY);
  if (stored && stored.trim()) {
    return stored.trim().replace(/\/+$/, "");
  }
  return (env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/+$/, "");
}

export function setStoredBackendUrl(url: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(BACKEND_URL_KEY, url.trim().replace(/\/+$/, ""));
  }
}

export function getStoredApiKey(): string {
  if (typeof window === "undefined") {
    return env.NEXT_PUBLIC_API_KEY || "dev-key-change-me";
  }
  const stored = localStorage.getItem(API_KEY_KEY);
  if (stored && stored.trim()) {
    return stored.trim();
  }
  return env.NEXT_PUBLIC_API_KEY || "dev-key-change-me";
}

export function setStoredApiKey(key: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(API_KEY_KEY, key.trim());
  }
}

