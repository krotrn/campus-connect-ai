"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Global critical error:", error);
  }, [error]);

  return (
    <html lang="en">
      <body className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-4 font-sans text-slate-900 dark:bg-slate-950 dark:text-slate-50">
        <div className="max-w-md text-center">
          <h1 className="text-3xl font-extrabold tracking-tight">
            Critical Application Error
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            A fatal error occurred in the root layout.
          </p>
          <button
            onClick={() => reset()}
            className="mt-6 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Restart Application
          </button>
        </div>
      </body>
    </html>
  );
}
