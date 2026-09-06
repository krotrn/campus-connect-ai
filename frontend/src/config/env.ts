import { z } from "zod";

const serverEnvSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
});

const clientEnvSchema = z.object({
  NEXT_PUBLIC_APP_URL: z.string().url().default("http://localhost:3000"),
  NEXT_PUBLIC_API_URL: z.string().default("http://localhost:8000"),
  NEXT_PUBLIC_API_KEY: z.string().default("dev-key-change-me"),
});

/**
 * Validate environment variables at build & runtime.
 */
function validateEnv() {
  const isServer = typeof window === "undefined";

  const parsedServer = serverEnvSchema.safeParse(process.env);
  if (!parsedServer.success && isServer) {
    console.error("❌ Invalid server environment variables:", parsedServer.error.flatten().fieldErrors);
    throw new Error("Invalid server environment variables");
  }

  const parsedClient = clientEnvSchema.safeParse({
    NEXT_PUBLIC_APP_URL: process.env.NEXT_PUBLIC_APP_URL,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_API_KEY: process.env.NEXT_PUBLIC_API_KEY,
  });

  if (!parsedClient.success) {
    console.error("❌ Invalid client environment variables:", parsedClient.error.flatten().fieldErrors);
    throw new Error("Invalid client environment variables");
  }

  return {
    ...(parsedServer.success ? parsedServer.data : {}),
    ...parsedClient.data,
  };
}

export const env = validateEnv();
