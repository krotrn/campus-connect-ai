import { describe, it, expect } from "vitest";
import { cn, formatDate, sleep } from "./utils";

describe("lib/utils", () => {
  describe("cn", () => {
    it("merges class names correctly", () => {
      const result = cn("text-red-500", "bg-blue-500");
      expect(result).toBe("text-red-500 bg-blue-500");
    });

    it("handles conditional classes properly", () => {
      const isHidden = false;
      const isVisible = true;
      const result = cn("p-4", isHidden && "hidden", isVisible && "block");
      expect(result).toBe("p-4 block");
    });

    it("merges conflicting Tailwind classes favoring the latter", () => {
      const result = cn("px-2 py-1", "p-4");
      expect(result).toBe("p-4");
    });
  });

  describe("formatDate", () => {
    it("formats a date string correctly", () => {
      const formatted = formatDate("2026-01-15T00:00:00.000Z");
      expect(formatted).toContain("2026");
      expect(formatted).toContain("Jan");
    });
  });

  describe("sleep", () => {
    it("resolves after delay", async () => {
      const start = Date.now();
      await sleep(50);
      const elapsed = Date.now() - start;
      expect(elapsed).toBeGreaterThanOrEqual(40);
    });
  });
});
