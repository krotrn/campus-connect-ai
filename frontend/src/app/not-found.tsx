import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { EmptyState } from "@/components/feedback/empty-state";
import { FileQuestion } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center p-4">
      <EmptyState
        icon={<FileQuestion className="size-16 text-muted-foreground" />}
        title="Page Not Found (404)"
        description="The page you are looking for does not exist or might have been moved."
        action={
          <Link href="/" className={buttonVariants({ variant: "default" })}>
            Return to Homepage
          </Link>
        }
      />
    </div>
  );
}
