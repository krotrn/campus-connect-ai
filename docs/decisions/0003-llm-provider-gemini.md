# ADR 0003: LLM Provider for V1 Answer Generation

## Status
Accepted

## Date
2026-09-02

## Context
V1 requires grounded question answering using retrieved chunks with source citations. To adhere to the project constraint of building a production-grade portfolio project with zero initial operating costs, the LLM provider must:
1. Provide a free tier capable of handling daily development and evaluation batches.
2. Have low latency and strong instruction-following for citation formatting.
3. Feature a large context window to accommodate multiple retrieved code chunks.

## Decision
We select **Google Gemini (Gemini 2.0 Flash / Gemini 1.5 Flash)** via Google AI Studio.

Key characteristics:
- Free tier allows up to 15 requests per minute (RPM) and 1,500 requests per day (RPD).
- 1M+ token context window, eliminating chunk truncation issues.
- Fast time-to-first-token (TTFT) and high reasoning quality for code explanation.
- Configured via standard SDK (`google-genai` and environment variable `GEMINI_API_KEY`).

## Consequences
- **Positive**: High speed, zero financial cost, native structured output capability.
- **Negative**: Free tier has a 15 RPM rate limit, which requires client-side rate-limit handling or backoff when running automated evaluation suites (addressed in V2 eval pipeline).

