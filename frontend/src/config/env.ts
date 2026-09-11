import { z } from "zod";

/**
 * Server-only configuration.
 *
 * AEIA_API_KEY must never be prefixed with NEXT_PUBLIC_: anything so prefixed is
 * inlined into the client bundle, which would publish the backend credential to
 * every visitor. The browser reaches the backend through the route handlers in
 * `src/app/api/aeia/*`, which attach this key server-side.
 */
const serverEnvSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  AEIA_API_URL: z.string().url().default("http://localhost:8000"),
  AEIA_API_KEY: z.string().default("dev-key-change-me"),
});

const clientEnvSchema = z.object({
  NEXT_PUBLIC_APP_URL: z.string().url().default("http://localhost:3000"),
});

export type ServerEnv = z.infer<typeof serverEnvSchema>;

function validateClientEnv() {
  const parsed = clientEnvSchema.safeParse({
    NEXT_PUBLIC_APP_URL: process.env.NEXT_PUBLIC_APP_URL,
  });

  if (!parsed.success) {
    console.error(
      "❌ Invalid client environment variables:",
      parsed.error.flatten().fieldErrors
    );
    throw new Error("Invalid client environment variables");
  }

  return parsed.data;
}

export const env = validateClientEnv();

/**
 * Read server-only configuration. Throws if called from the browser, so a
 * mistaken import into a client component fails loudly instead of leaking.
 */
export function getServerEnv(): ServerEnv {
  if (typeof window !== "undefined") {
    throw new Error("getServerEnv() must not be called from client code");
  }

  const parsed = serverEnvSchema.safeParse({
    NODE_ENV: process.env.NODE_ENV,
    AEIA_API_URL: process.env.AEIA_API_URL,
    AEIA_API_KEY: process.env.AEIA_API_KEY,
  });

  if (!parsed.success) {
    console.error(
      "❌ Invalid server environment variables:",
      parsed.error.flatten().fieldErrors
    );
    throw new Error("Invalid server environment variables");
  }

  if (
    parsed.data.NODE_ENV === "production" &&
    parsed.data.AEIA_API_KEY === "dev-key-change-me"
  ) {
    console.warn(
      "⚠️  AEIA_API_KEY is still the development default in production. Set a real key."
    );
  }

  return parsed.data;
}
