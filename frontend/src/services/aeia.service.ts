import { getStoredGeminiApiKey, resolveEndpoint } from "@/lib/settings";
import {
  AgentAskResponse,
  HealthResponse,
  SourceCitation,
  StreamPayload,
} from "@/types/aeia";

export interface StreamCallbacks {
  onSources?: (
    sources: SourceCitation[],
    sessionId?: string,
    rewrittenQuestion?: string,
    route?: string,
    routeReasoning?: string
  ) => void;
  onToken?: (token: string) => void;
  onDone?: (latencyMs: number, route?: string, model?: string | null) => void;
  onError?: (error: string) => void;
}

/** Pull a human-readable message out of an error response body. */
async function errorMessage(response: Response, fallback: string): Promise<string> {
  const data = await response.json().catch(() => null);
  if (!data) return fallback;

  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail
      .map((d: { msg?: string }) => d.msg || JSON.stringify(d))
      .join(", ");
  }
  if (typeof data.message === "string") return data.message;
  return fallback;
}

export const aeiaService = {
  /**
   * Ping the backend health endpoint.
   *
   * `overrideUrl` is used by the settings dialog to test a custom backend
   * before saving it; it bypasses the proxy and calls that host directly.
   */
  async checkHealth(overrideUrl?: string, overrideKey?: string): Promise<HealthResponse> {
    let url: string;
    let headers: Record<string, string>;

    if (overrideUrl?.trim()) {
      url = `${overrideUrl.trim().replace(/\/+$/, "")}/health`;
      headers = { Accept: "application/json" };
      if (overrideKey?.trim()) {
        headers["X-API-Key"] = overrideKey.trim();
      }
    } else {
      const resolved = resolveEndpoint("health");
      url = resolved.url;
      headers = { ...resolved.headers, Accept: "application/json" };
    }

    const res = await fetch(url, { method: "GET", headers });

    if (!res.ok) {
      throw new Error(await errorMessage(res, `Server responded with HTTP ${res.status}`));
    }

    return res.json();
  },

  /**
   * Stream a response from /ask/stream via Server-Sent Events (SSE).
   */
  async askStream(
    question: string,
    sessionId: string | null,
    callbacks: StreamCallbacks,
    signal?: AbortSignal
  ): Promise<void> {
    const { url, headers } = resolveEndpoint("askStream");
    const geminiApiKey = getStoredGeminiApiKey();

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({
        question,
        session_id: sessionId || undefined,
        stream: true,
        gemini_api_key: geminiApiKey || undefined,
      }),
      signal,
    });

    if (!response.ok) {
      throw new Error(await errorMessage(response, `Server error (${response.status})`));
    }

    if (!response.body) {
      throw new Error("No response body received from server");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data:")) continue;

          const jsonStr = trimmed.slice(5).trim();
          if (!jsonStr) continue;

          try {
            const payload = JSON.parse(jsonStr) as StreamPayload;

            if (payload.type === "sources") {
              callbacks.onSources?.(
                payload.sources || [],
                payload.session_id,
                payload.rewritten_question,
                payload.route,
                payload.route_reasoning
              );
            } else if (payload.type === "token") {
              callbacks.onToken?.(payload.text);
            } else if (payload.type === "done") {
              callbacks.onDone?.(payload.latency_ms, payload.route, payload.model);
            } else if (payload.type === "error") {
              callbacks.onError?.(payload.error || "Streaming error occurred");
            }
          } catch {
            // Ignore malformed JSON event chunks
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  },

  /**
   * Run the agent graph endpoint (/agent/ask) and wait for the full result.
   */
  async askAgent(
    question: string,
    sessionId: string | null,
    signal?: AbortSignal
  ): Promise<AgentAskResponse> {
    const { url, headers } = resolveEndpoint("agent");
    const geminiApiKey = getStoredGeminiApiKey();

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify({
        question,
        session_id: sessionId || undefined,
        gemini_api_key: geminiApiKey || undefined,
      }),
      signal,
    });

    if (!response.ok) {
      throw new Error(await errorMessage(response, `Agent request failed (${response.status})`));
    }

    return response.json();
  },
};
