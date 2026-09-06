export interface SourceCitation {
  file_path: string;
  chunk_id: string;
  score: number;
  content: string;
  start_line?: number | null;
  end_line?: number | null;
}

export interface HealthResponse {
  status: string;
  collection?: string;
  points_indexed?: number;
  indexed_points?: number;
  qdrant_url?: string;
}

export interface AskRequest {
  question: string;
  session_id?: string | null;
  stream?: boolean;
}

export interface AskResponse {
  answer: string;
  sources: SourceCitation[];
  session_id: string;
  latency_ms: number;
  model: string;
  rewritten_question?: string;
}

export interface AgentStep {
  step: string;
  thought?: string;
  action?: string;
  result?: unknown;
}

export interface AgentAskResponse {
  answer: string;
  session_id: string;
  route_taken: string;
  iterations: number;
  intermediate_steps?: AgentStep[];
  sources?: SourceCitation[];
}

export interface StreamSourcesPayload {
  type: "sources";
  sources: SourceCitation[];
  session_id?: string;
  rewritten_question?: string;
}

export interface StreamTokenPayload {
  type: "token";
  text: string;
}

export interface StreamDonePayload {
  type: "done";
  latency_ms: number;
}

export interface StreamErrorPayload {
  type: "error";
  error: string;
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
  model: string;
}

