import { backendHeaders, backendUrl, upstreamFailure } from "../proxy";

export async function POST(request: Request) {
  try {
    const payload = await request.text();

    const response = await fetch(backendUrl("/agent/ask"), {
      method: "POST",
      headers: backendHeaders(request, {
        "Content-Type": "application/json",
        Accept: "application/json",
      }),
      body: payload,
      signal: request.signal,
      cache: "no-store",
    });

    const body = await response.text();
    return new Response(body, {
      status: response.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    return upstreamFailure(error);
  }
}
