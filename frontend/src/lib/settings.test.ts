import { describe, it, expect, beforeEach } from "vitest";
import {
  PROXY_ROUTES,
  getCustomApiKey,
  getCustomBackendUrl,
  getStoredGeminiApiKey,
  isUsingCustomBackend,
  resolveEndpoint,
  setCustomApiKey,
  setCustomBackendUrl,
  setStoredGeminiApiKey,
} from "./settings";

describe("lib/settings", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("stores and retrieves a custom Gemini API key", () => {
    expect(getStoredGeminiApiKey()).toBe("");
    setStoredGeminiApiKey("AIzaSyTestCustomKey123");
    expect(getStoredGeminiApiKey()).toBe("AIzaSyTestCustomKey123");
  });

  it("normalizes a trailing slash off the custom backend URL", () => {
    setCustomBackendUrl("https://api.example.com/");
    expect(getCustomBackendUrl()).toBe("https://api.example.com");
  });

  it("stores a custom backend API key", () => {
    setCustomApiKey("custom-api-key");
    expect(getCustomApiKey()).toBe("custom-api-key");
  });

  it("clears a stored value when set to an empty string", () => {
    setCustomBackendUrl("https://api.example.com");
    setCustomBackendUrl("");
    expect(getCustomBackendUrl()).toBe("");
    expect(isUsingCustomBackend()).toBe(false);
  });

  describe("resolveEndpoint", () => {
    it("uses the same-origin proxy and sends no API key by default", () => {
      const { url, headers, direct } = resolveEndpoint("askStream");

      expect(url).toBe(PROXY_ROUTES.askStream);
      expect(direct).toBe(false);
      // The backend key lives on the server; it must never be attached here.
      expect(headers["X-API-Key"]).toBeUndefined();
    });

    it("calls a custom backend directly with the user's own key", () => {
      setCustomBackendUrl("https://my-aeia.example.com");
      setCustomApiKey("my-own-key");

      const { url, headers, direct } = resolveEndpoint("askStream");

      expect(url).toBe("https://my-aeia.example.com/ask/stream");
      expect(direct).toBe(true);
      expect(headers["X-API-Key"]).toBe("my-own-key");
    });

    it("forwards a stored Gemini key in both modes", () => {
      setStoredGeminiApiKey("AIzaSyUserKey");
      expect(resolveEndpoint("agent").headers["X-Gemini-API-Key"]).toBe("AIzaSyUserKey");

      setCustomBackendUrl("https://my-aeia.example.com");
      expect(resolveEndpoint("agent").headers["X-Gemini-API-Key"]).toBe("AIzaSyUserKey");
    });

    it("maps each route to the right backend path", () => {
      setCustomBackendUrl("https://my-aeia.example.com");

      expect(resolveEndpoint("health").url).toBe("https://my-aeia.example.com/health");
      expect(resolveEndpoint("askStream").url).toBe("https://my-aeia.example.com/ask/stream");
      expect(resolveEndpoint("agent").url).toBe("https://my-aeia.example.com/agent/ask");
    });
  });
});
