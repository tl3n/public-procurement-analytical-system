import { Database, Github } from "lucide-react";

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-border/60 bg-card/50 backdrop-blur-sm">
      <div className="container mx-auto flex flex-col items-start justify-between gap-2 py-5 text-xs text-muted-foreground sm:flex-row sm:items-center">
        <p className="flex items-center gap-2">
          <span className="inline-flex h-1.5 w-1.5 rounded-full bg-[hsl(var(--success))]" />
          <span>
            <span className="font-semibold text-foreground">
              ProcurementMonitor
            </span>{" "}
            · аналітична система моніторингу державних закупівель ·{" "}
            {year}
          </span>
        </p>
        <p className="flex items-center gap-4">
          <span className="inline-flex items-center gap-1.5">
            <Database className="h-3.5 w-3.5" />
            Дані Prozorro
            <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">
              public.api.openprocurement.org
            </code>
          </span>
          <span className="hidden items-center gap-1.5 sm:inline-flex">
            <Github className="h-3.5 w-3.5" />
            FastAPI · React · PostgreSQL
          </span>
        </p>
      </div>
    </footer>
  );
}
