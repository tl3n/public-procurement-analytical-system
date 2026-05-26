import { Outlet } from "@tanstack/react-router";

import { Footer } from "./Footer";
import { NavBar } from "./NavBar";

export function AppShell() {
  return (
    <div className="flex min-h-screen flex-col bg-transparent">
      <NavBar />
      <main className="container mx-auto flex-1 py-8">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
