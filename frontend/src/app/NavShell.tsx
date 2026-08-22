import type { ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { useLogout } from "@/hooks/useLogout";
import { useRole } from "@/hooks/useRole";
import { useSession } from "@/hooks/useSession";
import { useTheme } from "@/hooks/useTheme";

// Views, in the order a coach actually uses them (frontend/CLAUDE.md):
// Upcoming sessions -> Approvals -> Clients & companies.
const NAV_ITEMS = [
  { to: "/", label: "Upcoming sessions" },
  { to: "/approvals", label: "Approvals" },
  { to: "/clients", label: "Clients & companies" },
] as const;

export function NavShell({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useSession();
  const { isAdmin, user } = useRole();
  const canUseCoachLibrary = isAdmin || user?.role === "general";
  const location = useLocation();
  const logout = useLogout();
  const toast = useToast();
  const { theme, toggleTheme } = useTheme();

  if (!isAuthenticated || location.pathname === "/login") {
    return <>{children}</>;
  }

  async function handleLogout() {
    try {
      await logout.mutateAsync();
    } catch {
      toast.show("Failed to log out", "error");
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate/20 px-6 py-4 flex items-center justify-between">
        <span className="font-display text-lg">CoachFlow</span>
        <nav className="flex items-center gap-4 text-sm">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "text-teal font-medium" : "text-slate")}
              end={item.to === "/"}
            >
              {item.label}
            </NavLink>
          ))}
          {canUseCoachLibrary && (
            <NavLink
              to="/context-library"
              className={({ isActive }) => (isActive ? "text-teal font-medium" : "text-slate")}
            >
              Context Library
            </NavLink>
          )}
          {isAdmin && (
            <NavLink
              to="/admin/users"
              className={({ isActive }) => (isActive ? "text-teal font-medium" : "text-slate")}
            >
              Users
            </NavLink>
          )}
          {isAdmin && (
            <NavLink
              to="/admin/imports"
              className={({ isActive }) => (isActive ? "text-teal font-medium" : "text-slate")}
            >
              Import
            </NavLink>
          )}
          <NavLink to="/account" className={({ isActive }) => (isActive ? "text-teal font-medium" : "text-slate")}>
            Account
          </NavLink>
          <Button
            variant="secondary"
            className="px-3 py-1"
            onClick={toggleTheme}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {theme === "dark" ? "Light mode" : "Dark mode"}
          </Button>
          <Button variant="secondary" className="px-3 py-1" onClick={handleLogout} isLoading={logout.isPending}>
            Log out
          </Button>
        </nav>
      </header>
      <main className="flex-1 px-6 py-6">{children}</main>
    </div>
  );
}
