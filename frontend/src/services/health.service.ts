import { fetcher } from "@/lib/fetcher";
import { ApiResponse } from "@/types";

export interface HealthData {
  status: "healthy" | "unhealthy";
  uptime: number;
  environment: string;
}

export const healthService = {
  getHealth: async (): Promise<ApiResponse<HealthData>> => {
    return fetcher<ApiResponse<HealthData>>("/api/health");
  },
};
