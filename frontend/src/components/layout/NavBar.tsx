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
    <nav className="sticky top-0 z-30 border-b bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
      <div className="container mx-auto flex h-14 items-center justify-between">
        <Link
          to="/"
          className="flex items-center gap-2 font-semibold tracking-tight"
        >
          <span className="grid h-7 w-7 place-items-center rounded-md bg-primary text-primary-foreground">
            <BarChart3 className="h-4 w-4" />
          </span>
          <span className="hidden sm:inline">ProcurementMonitor</span>
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
