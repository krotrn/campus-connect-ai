import Link from "next/link";
import { siteConfig } from "@/config/site";
import { buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Code } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-8">
        <div className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg">
            <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-extrabold shadow-sm">
              IH
            </span>
            <span>{siteConfig.name}</span>
          </Link>
          <Badge variant="secondary" className="hidden sm:inline-flex gap-1 items-center font-medium">
            <Sparkles className="size-3 text-amber-500" /> Next.js 16 + shadcn/ui
          </Badge>
        </div>

        <nav className="flex items-center gap-4">
          <Link
            href="#features"
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Features
          </Link>
          <Link
            href="#architecture"
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Architecture
          </Link>
          <Link
            href="/api/health"
            target="_blank"
            className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            Health API
          </Link>
          <a
            href={siteConfig.links.github}
            target="_blank"
            rel="noreferrer"
            className={buttonVariants({ variant: "outline", size: "sm", className: "flex items-center gap-2" })}
          >
            <Code className="size-4" />
            <span>GitHub</span>
          </a>
        </nav>
      </div>
    </header>
  );
}
