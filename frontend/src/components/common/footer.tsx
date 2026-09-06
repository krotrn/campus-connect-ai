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
    <footer className="border-t border-border/40 bg-slate-950/60 py-6">
      <div className="container mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 sm:flex-row sm:px-6">
        <p className="text-center text-xs leading-loose text-muted-foreground sm:text-left">
          Powered by <span className="font-semibold text-foreground">Next.js 16</span>,{" "}
          <span className="font-semibold text-foreground">FastAPI</span>, and{" "}
          <span className="font-semibold text-foreground">LangGraph</span>.
        </p>
        <p className="text-center text-sm text-muted-foreground sm:text-right">
          &copy; {new Date().getFullYear()} {siteConfig.name}. Production Grade Setup.
        <p className="text-center text-xs text-muted-foreground sm:text-right">
          &copy; {new Date().getFullYear()} AEIA. Campus Connect Code Intelligence.
        </p>
      </div>
    </footer>
  );
}
