"use client";

import { useQuery } from "@tanstack/react-query";
import { healthService } from "@/services/health.service";

export const healthQueryKeys = {
  all: ["health"] as const,
};

export function useHealthQuery() {
  return useQuery({
    queryKey: healthQueryKeys.all,
    queryFn: () => healthService.getHealth(),
    staleTime: 30 * 1000,
  });
}
