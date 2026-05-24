import { useEffect } from "react";

interface Props {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}

/** Shared page header — renders an H1, an optional subtitle, an actions slot,
 *  and updates ``document.title`` so browser tabs are wayfinding-friendly. */
export function PageHeader({ title, description, actions }: Props) {
  useEffect(() => {
    const previous = document.title;
    document.title = `${title} · ProcurementMonitor`;
    return () => {
      document.title = previous;
    };
  }, [title]);

  return (
    <header className="flex flex-col gap-1 pb-2 sm:flex-row sm:items-end sm:justify-between sm:gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && (
          <p className="text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </header>
  );
}
