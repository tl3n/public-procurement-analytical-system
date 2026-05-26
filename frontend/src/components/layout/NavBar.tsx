import { Link } from "@tanstack/react-router";
import {
  BarChart3,
  LayoutDashboard,
  LineChart,
  ScrollText,
} from "lucide-react";

const links = [
  { to: "/", label: "Дашборд", icon: LayoutDashboard, exact: true },
  { to: "/tenders", label: "Тендери", icon: ScrollText, exact: false },
  { to: "/statistics", label: "Статистика", icon: LineChart, exact: false },
] as const;

export function NavBar() {
  return (
    <nav className="sticky top-0 z-30 border-b border-border/70 bg-card/85 backdrop-blur supports-[backdrop-filter]:bg-card/70">
      <div className="container mx-auto flex h-16 items-center justify-between gap-4">
        <Link
          to="/"
          className="group flex min-w-0 items-center gap-2.5"
        >
          <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md bg-primary text-primary-foreground shadow-sm shadow-primary/20 transition-transform group-hover:scale-[1.04]">
            <BarChart3 className="h-4 w-4" />
          </span>
          <span className="flex min-w-0 flex-col leading-tight">
            <span className="truncate text-sm font-bold tracking-tight">
              ProcurementMonitor
            </span>
            <span className="hidden text-[10px] uppercase tracking-[0.18em] text-muted-foreground sm:inline">
              Prozorro · аналітика
            </span>
          </span>
        </Link>
        <div className="flex items-center gap-1">
          {links.map(({ to, label, icon: Icon, exact }) => (
            <Link
              key={to}
              to={to}
              className="flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              activeProps={{
                className: "bg-primary/10 text-primary hover:bg-primary/15",
              }}
              activeOptions={{ exact }}
            >
              <Icon className="h-4 w-4" />
              <span className="hidden sm:inline">{label}</span>
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
