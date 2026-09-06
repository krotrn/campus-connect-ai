import { describe, it, expect, beforeEach } from "vitest";
import {
  getStoredApiKey,
  setStoredApiKey,
  getStoredBackendUrl,
  setStoredBackendUrl,
  getStoredGeminiApiKey,
  setStoredGeminiApiKey,
} from "./settings";

describe("lib/settings", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("stores and retrieves custom Gemini API key", () => {
    expect(getStoredGeminiApiKey()).toBe("");
    setStoredGeminiApiKey("AIzaSyTestCustomKey123");
    expect(getStoredGeminiApiKey()).toBe("AIzaSyTestCustomKey123");
  });

  it("stores and retrieves backend URL and API key", () => {
    setStoredBackendUrl("https://api.example.com/");
    expect(getStoredBackendUrl()).toBe("https://api.example.com");

    setStoredApiKey("custom-api-key");
    expect(getStoredApiKey()).toBe("custom-api-key");
  });
});

