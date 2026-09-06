import { LoadingSpinner } from "@/components/feedback/loading-spinner";

export default function Loading() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center p-8">
      <LoadingSpinner size="lg" label="Loading application..." />
    </div>
  );
}
