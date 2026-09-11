"use client";

import { useQuery } from "@tanstack/react-query";
import { aeiaService } from "@/services/aeia.service";
import { HealthResponse } from "@/types/aeia";

export const aeiaHealthQueryKeys = {
  all: ["aeia-health"] as const,
};

export type AeiaHealthStatus =
  | { state: "loading" }
  | { state: "healthy"; points: number }
  | { state: "offline" };

/**
 * Poll the AEIA backend's /health endpoint.
 *
 * Uses React Query rather than a useEffect + setInterval so the polling,
 * retry, and cleanup behaviour is declarative — and so the component does not
 * call setState from inside an effect.
 */
export function useAeiaHealthQuery() {
  return useQuery<HealthResponse>({
    queryKey: aeiaHealthQueryKeys.all,
    queryFn: () => aeiaService.checkHealth(),
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
    retry: false,
    staleTime: 15_000,
  });
}

/**
 * Collapse the query result into the shape the sidebar renders, plus a manual
 * refresh for the "click to re-check" affordance.
 */
export function useAeiaHealthStatus(): {
  status: AeiaHealthStatus;
  refetch: () => void;
} {
  const { data, isPending, isError, refetch } = useAeiaHealthQuery();

  let status: AeiaHealthStatus;
  if (isPending) {
    status = { state: "loading" };
  } else if (isError || !data) {
    status = { state: "offline" };
  } else {
    status = {
      state: "healthy",
      points: data.points_indexed ?? data.indexed_points ?? 0,
    };
  }

  return { status, refetch: () => void refetch() };
}
