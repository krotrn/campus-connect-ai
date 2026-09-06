import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useHealthQuery } from "./use-health";
import { healthService } from "@/services/health.service";
import React from "react";

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  function QueryWrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return QueryWrapper;
};

describe("useHealthQuery", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches and returns health API payload successfully", async () => {
    const mockData = {
      success: true,
      data: {
        status: "healthy" as const,
        uptime: 120,
        environment: "test",
      },
      meta: {
        timestamp: "2026-09-01T20:00:00.000Z",
        version: "1.0.0",
      },
    };

    vi.spyOn(healthService, "getHealth").mockResolvedValueOnce(mockData);

    const { result } = renderHook(() => useHealthQuery(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isPending).toBe(true);

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockData);
    expect(result.current.data?.data?.status).toBe("healthy");
  });
});
