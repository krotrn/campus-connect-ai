import { siteConfig } from "@/config/site";

export function Footer() {
  return (
    <footer className="border-t border-border/40 bg-muted/30 py-8">
      <div className="container mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 sm:flex-row sm:px-8">
        <p className="text-center text-sm leading-loose text-muted-foreground sm:text-left">
          Built with{" "}
          <span className="font-semibold text-foreground">Next.js 16</span>,{" "}
          <span className="font-semibold text-foreground">TypeScript</span>, and{" "}
          <span className="font-semibold text-foreground">shadcn/ui</span>.
        </p>
        <p className="text-center text-sm text-muted-foreground sm:text-right">
          &copy; {new Date().getFullYear()} {siteConfig.name}. Production Grade Setup.
        </p>
      </div>
    </footer>
  );
}
