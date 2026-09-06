import { test, expect } from "@playwright/test";

test.describe("Home Page", () => {
  test("loads landing page and renders heading and buttons", async ({ page }) => {
    await page.goto("/");

    // Verify main heading
    await expect(page.locator("h1")).toContainText("Next.js 16");

    // Verify CTA button
    const demoButton = page.getByRole("link", { name: /try live interactive demo/i });
    await expect(demoButton).toBeVisible();
  });

  test("renders TanStack Query demo and refetches data", async ({ page }) => {
    await page.goto("/");

    // Verify Query tab is active by default
    await expect(page.getByText("Live Server State (TanStack Query)")).toBeVisible();
    await expect(page.getByText("GET /api/health")).toBeVisible();

    // Click Refetch Query button
    const refetchButton = page.getByRole("button", { name: /refetch query/i });
    await expect(refetchButton).toBeVisible();
    await refetchButton.click();
  });

  test("switches tabs and filters candidate list using search input", async ({ page }) => {
    await page.goto("/");

    // Switch to Candidate Search tab
    const candidateTab = page.getByRole("tab", { name: /candidate search demo/i });
    await candidateTab.click();

    // Find search input in candidate explorer
    const searchInput = page.getByPlaceholder("Search by candidate name, role, or technology...");
    await expect(searchInput).toBeVisible();

    // Type query
    await searchInput.fill("Sarah");

    // Check filtered candidate visible
    await expect(page.getByText("Sarah Chen")).toBeVisible();
    await expect(page.getByText("David Kim")).not.toBeVisible();
  });
});
