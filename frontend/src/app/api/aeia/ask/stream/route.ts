import { backendHeaders, backendUrl, upstreamFailure } from "../../proxy";

// Route Handlers are uncached by default in Next 16, and the fetches below
// set `cache: "no-store"`, so no route segment config is needed here.

export async function POST(request: Request) {
  try {
    const payload = await request.text();

    const response = await fetch(backendUrl("/ask/stream"), {
      method: "POST",
      headers: backendHeaders(request, {
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      }),
      body: payload,
      // Forward the client's cancellation so a stopped generation stops upstream.
      signal: request.signal,
      cache: "no-store",
    });

    if (!response.ok || !response.body) {
      const text = await response.text();
      return new Response(text || JSON.stringify({ message: "Upstream error" }), {
        status: response.status,
        headers: { "Content-Type": "application/json" },
      });
    }

    return new Response(response.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error) {
    return upstreamFailure(error);
  }
}
