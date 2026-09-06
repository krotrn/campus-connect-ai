import { test, expect } from "@playwright/test";

test.describe("API Health Endpoint", () => {
  test("returns healthy status via HTTP GET", async ({ request }) => {
    const response = await request.get("/api/health");
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);

    const body = await response.json();
    expect(body).toMatchObject({
      success: true,
      data: {
        status: "healthy",
      },
    });
  });
});
