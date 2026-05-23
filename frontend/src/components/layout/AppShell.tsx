import { Outlet } from "@tanstack/react-router";

import { NavBar } from "./NavBar";

export function AppShell() {
  return (
    <div className="min-h-screen bg-background">
      <NavBar />
      <main className="container mx-auto py-6">
        <Outlet />
      </main>
    </div>
  );
}
