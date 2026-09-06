# ADR 0029: Client-Side Dynamic API Key Injection & LLM Quota Resilience

## Status

Accepted

## Date

2026-09-07

## Context

AEIA relies on Google Gemini (`gemini-2.0-flash` / `gemini-3.6-flash`) via the Google GenAI SDK for grounded answer generation, coreference query reformulation, and evaluation judging ([ADR 0003](0003-llm-provider-gemini.md), [ADR 0025](0025-conversational-memory-and-coreference-rewriter.md)). 

On the Google AI Studio free tier, API usage is governed by strict rate limits:
* 15 Requests Per Minute (RPM)
* 1,500 Requests Per Day (RPD)
* Token-per-minute throughput caps

When AEIA is deployed publicly (e.g. for portfolio reviews, recruiter evaluations, or team testing), all visitors share the single `GEMINI_API_KEY` defined in the server environment. If one user runs a heavy evaluation benchmark or multiple users query concurrently, the server encounters `429 RESOURCE_EXHAUSTED` (`LLMQuotaExceededError`). In earlier versions, this resulted in an unavoidable outage for all subsequent visitors until Google's rate-limiting window elapsed.

## Decision

We implemented **Dynamic Per-Request Client API Key Injection** combined with **Automated Client-Side Quota Backoff & Recovery**.

```mermaid
sequenceDiagram
    autonumber
    actor User as Web Console User
    participant Frontend as Next.js Console (localStorage)
    participant API as FastAPI Gateway
    participant Gen as AnswerGenerator
    participant Gemini as Google Gemini API

    User->>Frontend: Submit Question
    Frontend->>Frontend: Check localStorage for user Gemini key
    Frontend->>API: POST /ask/stream with X-Gemini-API-Key (or body)
    
    API->>Gen: _resolve_client(effective_api_key)
    alt Client Key Provided
        Note over Gen: Instantiate ephemeral genai.Client(user_key)
    else No Client Key
        Note over Gen: Use shared server genai.Client
    end

    Gen->>Gemini: Stream Generation
    alt Successful Generation
        Gemini-->>Gen: Stream Chunks
        Gen-->>API-->>Frontend: Token Stream & Done
    else Shared Quota Exhausted (429)
        Gemini-->>Gen: 429 RESOURCE_EXHAUSTED
        Gen-->>API: Raise LLMQuotaExceededError(retry_after=60)
        API-->>Frontend: HTTP 429 { error: "LLM_QUOTA_EXHAUSTED", retry_after: 60 }
        Frontend->>Frontend: Render QuotaAlert with animated countdown
        User->>Frontend: Provide own key in QuotaAlert modal
        Frontend->>API: Retry query with user key -> Success!
    end
```

### 1. Dynamic Client Resolution (`src/generation/generator.py`)
`AnswerGenerator` now supports dynamic client resolution without mutating the global singleton:
```python
def _resolve_client(self, api_key: str | None = None) -> tuple[genai.Client | None, bool]:
    clean_key = (api_key or "").strip()
    if clean_key and clean_key != "your_gemini_api_key_here":
        return genai.Client(api_key=clean_key), True
    return self.client, False
```
* If a request provides a custom key, an ephemeral client is instantiated strictly for the scope of that generation.
* If omitted, the generator gracefully falls back to the server-configured `settings.gemini_api_key`.

### 2. Multi-Channel Request Propagation (`src/api/main.py`)
The effective key is extracted from either HTTP headers or the JSON payload:
```python
effective_gemini_key = (
    (body.gemini_api_key or "").strip()
    or request.headers.get("x-gemini-api-key", "").strip()
    or request.headers.get("X-Gemini-API-Key", "").strip()
    or None
)
```
This key is passed downstream to:
- `rewrite_query_with_history(..., client=rewriter_client)` (coreference reformulation)
- `generator.generate()` and `generator.generate_stream()` (answer synthesis)
- `agent.invoke({"gemini_api_key": effective_gemini_key})` (LangGraph state machine)

### 3. Frontend Settings & QuotaAlert Recovery (`frontend/src/components/aeia/`)
- **`SettingsDialog`**: Allows developers and evaluators to input a personal Gemini API key. Keys are persisted in browser `localStorage` and never transmitted to database storage or logged on the server.
- **`QuotaAlert`**: Listens for HTTP 429 errors from the backend. When triggered:
  1. Parses the `Retry-After` header or default backoff interval.
  2. Displays a real-time countdown progress bar.
  3. Prompts the user with a 1-click modal to input their own free-tier key and automatically retries the failed query (`handleSaveAndRetry`).

## Consequences

### Positive
- **Zero Downtime for Evaluators**: Reviewers and recruiters are never blocked by shared server rate limits; they can supply their own key in 10 seconds.
- **Strict Privacy & Security**: User API keys exist only in the user's browser `localStorage` and memory during the duration of their HTTP request. Keys are never written to disk, telemetry traces, or databases.
- **Graceful Error UX**: Instead of an obscure JSON error or blank screen, users receive an actionable alert with clear instructions, an animated timer, and an immediate recovery path.

### Trade-Offs
- Instantiating an ephemeral `genai.Client` per request when custom keys are used adds ~1-2ms of object creation overhead, which is negligible compared to network TTFT (<400ms).

## Validation

- `pytest tests/test_error_handling.py` (verifies custom API key overrides, client resolution, and HTTP 429 exception handling).
- Frontend Vitest suite `frontend/src/lib/settings.test.ts` (verifies local storage persistence and retrieval).

