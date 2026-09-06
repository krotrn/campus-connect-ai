import { NextResponse } from "next/server";
import { ApiResponse } from "@/types";

export async function GET() {
  const payload: ApiResponse<{
    status: "healthy" | "unhealthy";
    uptime: number;
    environment: string;
  }> = {
    success: true,
    data: {
      status: "healthy",
      uptime: process.uptime ? Math.floor(process.uptime()) : 0,
      environment: process.env.NODE_ENV || "development",
    },
    meta: {
      timestamp: new Date().toISOString(),
      version: "1.0.0",
    },
  };

  return NextResponse.json(payload, { status: 200 });
}
