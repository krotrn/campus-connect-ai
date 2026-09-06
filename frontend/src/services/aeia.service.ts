import { getStoredApiKey, getStoredBackendUrl } from "@/lib/settings";
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
  onDone?: (latencyMs: number, route?: string) => void;
  onError?: (error: string) => void;
}

export const aeiaService = {
  /**
   * Ping backend health endpoint.
   */
  async checkHealth(overrideUrl?: string): Promise<HealthResponse> {
    const baseUrl = (overrideUrl || getStoredBackendUrl()).replace(/\/+$/, "");
    const res = await fetch(`${baseUrl}/health`, {
      method: "GET",
      headers: {
        Accept: "application/json",
      },
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Server responded with HTTP ${res.status}`);
    }

    return res.json();
  },

  /**
   * Stream response from /ask/stream via Server-Sent Events (SSE).
   */
  async askStream(
    question: string,
    sessionId: string | null,
    callbacks: StreamCallbacks,
    signal?: AbortSignal
  ): Promise<void> {
    const baseUrl = getStoredBackendUrl();
    const apiKey = getStoredApiKey();

    const response = await fetch(`${baseUrl}/ask/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify({
        question,
        session_id: sessionId || undefined,
        stream: true,
      }),
      signal,
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      let msg = `Server error (${response.status})`;
      if (typeof errData.detail === "string") {
        msg = errData.detail;
      } else if (Array.isArray(errData.detail)) {
        msg = errData.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join(", ");
      } else if (errData.message) {
        msg = errData.message;
      }
      throw new Error(msg);
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
              callbacks.onDone?.(payload.latency_ms, payload.route);
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
   * Run agent graph endpoint /agent/ask.
   */
  async askAgent(
    question: string,
    sessionId: string | null,
    signal?: AbortSignal
  ): Promise<AgentAskResponse> {
    const baseUrl = getStoredBackendUrl();
    const apiKey = getStoredApiKey();

    const response = await fetch(`${baseUrl}/agent/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey,
      },
      body: JSON.stringify({
        question,
        session_id: sessionId || undefined,
      }),
      signal,
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      let msg = `Agent request failed (${response.status})`;
      if (typeof errData.detail === "string") {
        msg = errData.detail;
      } else if (errData.message) {
        msg = errData.message;
      }
      throw new Error(msg);
    }

    return response.json();
  },
};

