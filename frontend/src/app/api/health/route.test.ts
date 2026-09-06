import { describe, it, expect } from "vitest";
import { GET } from "./route";

describe("GET /api/health", () => {
  it("returns 200 OK with healthy status payload", async () => {
    const response = await GET();
    expect(response.status).toBe(200);

    const data = await response.json();
    expect(data).toHaveProperty("success", true);
    expect(data.data).toHaveProperty("status", "healthy");
    expect(data.meta).toHaveProperty("version", "1.0.0");
    expect(data.meta).toHaveProperty("timestamp");
  });
});
