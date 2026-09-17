import { cn } from "@/lib/utils";

interface LoadingSpinnerProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  label?: string;
}

export function LoadingSpinner({
  size = "md",
  className,
  label = "Loading...",
}: LoadingSpinnerProps) {
  const sizeStyles = {
    sm: "h-4 w-4 border-2",
    md: "h-8 w-8 border-3",
    lg: "h-12 w-12 border-4",
  };

  return (
    <div
      className="flex flex-col items-center justify-center gap-2"
      role="status"
      aria-label={label}
    >
      <div
        className={cn(
          "animate-spin rounded-full border-solid border-moss-500 border-t-transparent",
          sizeStyles[size],
          className
        )}
      />
      {label && <span className="text-xs text-muted-foreground">{label}</span>}
    </div>
  );
}
