import { getServerEnv } from "@/config/env";

/**
 * Server-side proxy helpers for the AEIA backend.
 *
 * The browser never holds the backend API key. It calls these Next route
 * handlers on its own origin; they attach `X-API-Key` from server-only
 * configuration and forward to the FastAPI service.
 *
 * The caller's own Gemini key (which belongs to the user, not the server) is
 * the one header we do pass through.
 */

const GEMINI_HEADER = "x-gemini-api-key";

export function backendUrl(path: string): string {
  const { AEIA_API_URL } = getServerEnv();
  return `${AEIA_API_URL.replace(/\/+$/, "")}${path}`;
}

export function backendHeaders(request: Request, extra?: HeadersInit): Headers {
  const { AEIA_API_KEY } = getServerEnv();
  const headers = new Headers(extra);
  headers.set("X-API-Key", AEIA_API_KEY);

  const geminiKey = request.headers.get(GEMINI_HEADER);
  if (geminiKey) {
    headers.set("X-Gemini-API-Key", geminiKey);
  }

  return headers;
}

export function upstreamFailure(error: unknown): Response {
  const message =
    error instanceof Error && error.name === "AbortError"
      ? "Request to the AEIA backend was aborted."
      : "Could not reach the AEIA backend. Check that it is running and AEIA_API_URL is correct.";

  console.error("AEIA proxy error:", error);
  return Response.json({ error: "BACKEND_UNREACHABLE", message }, { status: 502 });
}
