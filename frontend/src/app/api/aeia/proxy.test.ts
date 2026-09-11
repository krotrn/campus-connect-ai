// @vitest-environment node
//
// These are server-only route handlers. getServerEnv() deliberately throws when
// `window` exists, so they must be exercised in a Node environment rather than
// the project-wide happy-dom default.
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

/**
 * The point of these route handlers is that the backend API key never reaches
 * the browser. These tests pin that: the handler must attach the key itself,
 * and must not trust one supplied by the caller.
 */

const ORIGINAL_ENV = { ...process.env };

beforeEach(() => {
  vi.resetModules();
  process.env.AEIA_API_URL = "http://backend.test:8000";
  process.env.AEIA_API_KEY = "server-side-secret";
});

afterEach(() => {
  process.env = { ...ORIGINAL_ENV };
  vi.restoreAllMocks();
});

describe("AEIA proxy helpers", () => {
  it("builds backend URLs without duplicating slashes", async () => {
    process.env.AEIA_API_URL = "http://backend.test:8000/";
    const { backendUrl } = await import("./proxy");

    expect(backendUrl("/health")).toBe("http://backend.test:8000/health");
  });

  it("attaches the server-side API key", async () => {
    const { backendHeaders } = await import("./proxy");
    const headers = backendHeaders(new Request("http://localhost/api/aeia/health"));

    expect(headers.get("X-API-Key")).toBe("server-side-secret");
  });

  it("ignores an API key supplied by the caller", async () => {
    const { backendHeaders } = await import("./proxy");
    const headers = backendHeaders(
      new Request("http://localhost/api/aeia/health", {
        headers: { "X-API-Key": "attacker-supplied" },
      })
    );

    expect(headers.get("X-API-Key")).toBe("server-side-secret");
  });

  it("forwards the caller's own Gemini key", async () => {
    const { backendHeaders } = await import("./proxy");
    const headers = backendHeaders(
      new Request("http://localhost/api/aeia/ask/stream", {
        headers: { "X-Gemini-API-Key": "AIzaSyUserKey" },
      })
    );

    expect(headers.get("X-Gemini-API-Key")).toBe("AIzaSyUserKey");
  });

  it("returns 502 rather than throwing when the backend is unreachable", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const { upstreamFailure } = await import("./proxy");

    const response = upstreamFailure(new TypeError("fetch failed"));
    expect(response.status).toBe(502);
    await expect(response.json()).resolves.toMatchObject({
      error: "BACKEND_UNREACHABLE",
    });
  });
});

describe("GET /api/aeia/health", () => {
  it("proxies to the backend with the server key and relays the body", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify({ status: "healthy", points_indexed: 42 }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        })
      );

    const { GET } = await import("./health/route");
    const response = await GET(new Request("http://localhost/api/aeia/health"));

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toMatchObject({ points_indexed: 42 });

    const [calledUrl, init] = fetchMock.mock.calls[0];
    expect(calledUrl).toBe("http://backend.test:8000/health");
    expect(new Headers(init?.headers).get("X-API-Key")).toBe("server-side-secret");
  });

  it("surfaces a backend failure as 502 instead of crashing", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fetch failed"));

    const { GET } = await import("./health/route");
    const response = await GET(new Request("http://localhost/api/aeia/health"));

    expect(response.status).toBe(502);
  });
});

describe("POST /api/aeia/ask/stream", () => {
  it("passes the SSE body through with streaming headers", async () => {
    const upstream = new Response("data: {\"type\":\"token\",\"text\":\"hi\"}\n\n", {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(upstream);

    const { POST } = await import("./ask/stream/route");
    const response = await POST(
      new Request("http://localhost/api/aeia/ask/stream", {
        method: "POST",
        body: JSON.stringify({ question: "Where is auth?" }),
      })
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("Content-Type")).toBe("text/event-stream");
    expect(response.headers.get("X-Accel-Buffering")).toBe("no");
    await expect(response.text()).resolves.toContain("data:");
  });

  it("relays an upstream error status and body", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ message: "Invalid or missing API key" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      })
    );

    const { POST } = await import("./ask/stream/route");
    const response = await POST(
      new Request("http://localhost/api/aeia/ask/stream", {
        method: "POST",
        body: JSON.stringify({ question: "Where is auth?" }),
      })
    );

    expect(response.status).toBe(401);
  });
});
