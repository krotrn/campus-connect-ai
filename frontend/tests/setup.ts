import { afterEach, vi } from "vitest";

// This setup file runs for every test file, including the server-only route
// handler suites that opt into `@vitest-environment node`. Anything touching the
// DOM has to be guarded so those suites do not fail on a missing `window`.
const hasDom = typeof window !== "undefined";

if (hasDom) {
  await import("@testing-library/jest-dom/vitest");
  const { cleanup } = await import("@testing-library/react");

  // Automatically cleanup DOM after each test
  afterEach(() => {
    cleanup();
  });

  // Polyfill window.matchMedia with standard modern EventTarget API
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => {
      const listeners = new Set<(event: MediaQueryListEvent) => void>();

      return {
        matches: false,
        media: query,
        onchange: null,
        addEventListener: vi.fn(
          (type: string, listener: (event: MediaQueryListEvent) => void) => {
            if (type === "change") {
              listeners.add(listener);
            }
          }
        ),
        removeEventListener: vi.fn(
          (type: string, listener: (event: MediaQueryListEvent) => void) => {
            if (type === "change") {
              listeners.delete(listener);
            }
          }
        ),
        dispatchEvent: vi.fn((event: Event) => {
          listeners.forEach((listener) => listener(event as MediaQueryListEvent));
          return true;
        }),
      };
    }),
  });
}
