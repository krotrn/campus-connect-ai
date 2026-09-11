import { backendHeaders, backendUrl, upstreamFailure } from "../proxy";

export async function GET(request: Request) {
  try {
    const response = await fetch(backendUrl("/health"), {
      method: "GET",
      headers: backendHeaders(request, { Accept: "application/json" }),
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
