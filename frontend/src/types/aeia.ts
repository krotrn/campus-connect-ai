/**
 * Wire types for the AEIA backend.
 *
 * These mirror the Pydantic models in `src/api/main.py` and
 * `src/generation/generator.py`. Keep them in step with those definitions.
 */

export interface SourceCitation {
  file_path: string;
  start_line: number;
  end_line: number;
  /** Pre-rendered "path#Lstart-Lend" reference. */
  citation: string;
  content?: string | null;
  score?: number | null;
}

export interface HealthResponse {
  status: string;
  collection?: string;
  points_indexed?: number;
  /** Deprecated alias of points_indexed, kept for older backends. */
  indexed_points?: number;
  qdrant_url?: string;
}

export interface AskRequest {
  question: string;
  top_k?: number;
  use_agent?: boolean;
  session_id?: string | null;
  stream?: boolean;
  gemini_api_key?: string;
}

export interface AskResponse {
  question: string;
  answer: string;
  sources: SourceCitation[];
  latency_ms: number;
  session_id?: string | null;
  rewritten_question?: string | null;
  route?: string | null;
  route_reasoning?: string | null;
  /** Model that actually produced the answer, after any fallback. */
  model?: string | null;
}

export interface AgentAskResponse {
  question: string;
  route: string;
  route_reasoning: string;
  tool_output?: string | null;
  answer: string;
  sources: SourceCitation[];
  steps_taken: string[];
  latency_ms: number;
  session_id?: string | null;
  rewritten_question?: string | null;
}

export interface StreamSourcesPayload {
  type: "sources";
  sources: SourceCitation[];
  session_id?: string;
  rewritten_question?: string;
  route?: string;
  route_reasoning?: string;
}

export interface StreamTokenPayload {
  type: "token";
  text: string;
}

export interface StreamDonePayload {
  type: "done";
  latency_ms: number;
  session_id?: string;
  route?: string;
  route_reasoning?: string;
  /** Model that actually produced the answer, after any fallback. */
  model?: string | null;
}

export interface StreamErrorPayload {
  type: "error";
  error: string;
  code?: string;
}

export type StreamPayload =
  | StreamSourcesPayload
  | StreamTokenPayload
  | StreamDonePayload
  | StreamErrorPayload;

export type ExecutionMode = "rag" | "agent";

export interface TelemetryData {
  route: string;
  latency: string;
  chunks: number;
  /** Null until the backend reports which model answered. */
  model: string | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceCitation[];
  telemetry?: TelemetryData | null;
  rewrittenQuery?: string | null;
  isStreaming?: boolean;
  timestamp: number;
}
