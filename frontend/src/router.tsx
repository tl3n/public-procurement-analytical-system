import {
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";

import { AppShell } from "./components/layout/AppShell";
import { Dashboard } from "./routes/Dashboard";
import { Statistics } from "./routes/Statistics";
import { TenderDetail } from "./routes/TenderDetail";
import { TenderList } from "./routes/TenderList";

// Code-based route tree — explicit, no codegen step. File-based routing is a
// reasonable migration target once the route tree grows.
const rootRoute = createRootRoute({ component: AppShell });

const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: Dashboard,
});

const tenderListRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/tenders",
  component: TenderList,
});

const tenderDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/tenders/$id",
  component: TenderDetail,
});

const statisticsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/statistics",
  component: Statistics,
});

const routeTree = rootRoute.addChildren([
  dashboardRoute,
  tenderListRoute,
  tenderDetailRoute,
  statisticsRoute,
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}
