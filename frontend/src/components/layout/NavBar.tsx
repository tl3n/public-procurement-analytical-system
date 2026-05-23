import { Link } from "@tanstack/react-router";

const links = [
  { to: "/", label: "Дашборд" },
  { to: "/tenders", label: "Тендери" },
  { to: "/statistics", label: "Статистика" },
] as const;

export function NavBar() {
  return (
    <nav className="border-b bg-card">
      <div className="container mx-auto flex h-14 items-center justify-between">
        <div className="font-semibold tracking-tight">ProcurementMonitor</div>
        <div className="flex gap-6">
          {links.map((l) => (
            <Link
              key={l.to}
              to={l.to}
              className="text-sm font-medium text-muted-foreground hover:text-foreground"
              activeProps={{ className: "text-foreground font-semibold" }}
              activeOptions={{ exact: l.to === "/" }}
            >
              {l.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
