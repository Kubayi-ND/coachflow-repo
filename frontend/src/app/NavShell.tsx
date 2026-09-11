import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";

import {
  BellIcon,
  BookIcon,
  CalendarIcon,
  CheckCircleIcon,
  LogOutIcon,
  MenuIcon,
  MoonIcon,
  SettingsIcon,
  SunIcon,
  UploadIcon,
  UserIcon,
  UsersIcon,
  XIcon,
} from "@/components/ui/icons";
import { useToast } from "@/components/ui/Toast";
import { useDrafts } from "@/hooks/useDrafts";
import { useLogout } from "@/hooks/useLogout";
import { useRole } from "@/hooks/useRole";
import { useSession } from "@/hooks/useSession";
import { useTheme } from "@/hooks/useTheme";

interface NavItem {
  to: string;
  label: string;
  icon: (props: { className?: string }) => ReactNode;
  end?: boolean;
  badge?: number;
}

const PAGE_TITLES: { test: (path: string) => boolean; title: string }[] = [
  { test: (p) => p === "/", title: "Upcoming sessions" },
  { test: (p) => p.startsWith("/approvals"), title: "Approvals" },
  { test: (p) => p.startsWith("/clients"), title: "Clients & companies" },
  { test: (p) => p.startsWith("/sessions/") && p.endsWith("/scorecard"), title: "Scorecard" },
  { test: (p) => p.startsWith("/context-library"), title: "Context Library" },
  { test: (p) => p.startsWith("/admin/users"), title: "Users" },
  { test: (p) => p.startsWith("/admin/imports"), title: "Import" },
  { test: (p) => p.startsWith("/account"), title: "Account" },
];

function pageTitleFor(pathname: string): string {
  return PAGE_TITLES.find((entry) => entry.test(pathname))?.title ?? "CoachFlow";
}

export function NavShell({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useSession();
  const { isAdmin, user } = useRole();
  const canUseCoachLibrary = isAdmin || user?.role === "general";
  const location = useLocation();
  const navigate = useNavigate();
  const logout = useLogout();
  const toast = useToast();
  const { theme, toggleTheme } = useTheme();
  const { data: drafts } = useDrafts();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    setMobileNavOpen(false);
  }, [location.pathname]);

  if (!isAuthenticated || location.pathname === "/login") {
    return <>{children}</>;
  }

  const pendingCount = drafts?.length ?? 0;

  const primaryItems: NavItem[] = [
    { to: "/", label: "Upcoming sessions", icon: CalendarIcon, end: true },
    { to: "/approvals", label: "Approvals", icon: CheckCircleIcon, badge: pendingCount },
    { to: "/clients", label: "Clients", icon: UsersIcon },
  ];
  const libraryItems: NavItem[] = canUseCoachLibrary
    ? [{ to: "/context-library", label: "Context Library", icon: BookIcon }]
    : [];
  const adminItems: NavItem[] = isAdmin
    ? [
        { to: "/admin/users", label: "Users", icon: UserIcon },
        { to: "/admin/imports", label: "Import", icon: UploadIcon },
      ]
    : [];

  async function handleLogout() {
    try {
      await logout.mutateAsync();
    } catch {
      toast.show("Failed to log out", "error");
    }
  }

  const initials = (user?.email ?? "?").slice(0, 2).toUpperCase();

  return (
    <div className="flex min-h-screen bg-paper">
      {/* Desktop / tablet rail — icon-only at md, full labels at lg+. Sticky +
          h-screen pins it to the viewport instead of stretching to match
          the (possibly taller) content column and scrolling away with it. */}
      <aside
        className="hidden md:sticky md:top-0 md:flex md:h-screen md:w-16 md:flex-shrink-0 md:flex-col md:self-start lg:w-60 bg-sidebar-bg"
        aria-label="Primary navigation"
      >
        <SidebarContent
          primaryItems={primaryItems}
          libraryItems={libraryItems}
          adminItems={adminItems}
          collapsedLabels
          initials={initials}
          email={user?.email}
          theme={theme}
          onToggleTheme={toggleTheme}
          onLogout={handleLogout}
          isLoggingOut={logout.isPending}
        />
      </aside>

      {/* Mobile slide-over drawer. */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-30 md:hidden">
          <div className="absolute inset-0 bg-ink/40" onClick={() => setMobileNavOpen(false)} aria-hidden="true" />
          <aside
            className="absolute left-0 top-0 flex h-full w-72 flex-col bg-sidebar-bg shadow-panel"
            role="dialog"
            aria-modal="true"
            aria-label="Navigation"
            onKeyDown={(e) => e.key === "Escape" && setMobileNavOpen(false)}
          >
            <div className="flex items-center justify-between px-5 py-5">
              <span className="font-display text-base text-white">CoachFlow</span>
              <button
                type="button"
                className="text-sidebar-fg/70 hover:text-white"
                aria-label="Close navigation"
                onClick={() => setMobileNavOpen(false)}
              >
                <XIcon className="h-5 w-5" />
              </button>
            </div>
            <SidebarContent
              primaryItems={primaryItems}
              libraryItems={libraryItems}
              adminItems={adminItems}
              initials={initials}
              email={user?.email}
              theme={theme}
              onToggleTheme={toggleTheme}
              onLogout={handleLogout}
              isLoggingOut={logout.isPending}
              skipLogo
            />
          </aside>
        </div>
      )}

      <div className="flex min-h-screen flex-1 flex-col">
        <header className="flex h-16 flex-shrink-0 items-center justify-between border-b border-border bg-surface px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="text-slate hover:text-ink md:hidden"
              aria-label="Open navigation"
              onClick={() => setMobileNavOpen(true)}
            >
              <MenuIcon className="h-5 w-5" />
            </button>
            <h1 className="font-display text-lg text-ink">{pageTitleFor(location.pathname)}</h1>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="relative text-slate hover:text-ink"
              aria-label={pendingCount > 0 ? `${pendingCount} drafts pending approval` : "No drafts pending approval"}
              onClick={() => navigate("/approvals")}
            >
              <BellIcon className="h-5 w-5" />
              {pendingCount > 0 && (
                <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-amber px-1 text-[10px] font-semibold text-white tabular-nums">
                  {pendingCount}
                </span>
              )}
            </button>
            <button
              type="button"
              className="text-slate hover:text-ink"
              onClick={toggleTheme}
              aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            >
              {theme === "dark" ? <SunIcon className="h-5 w-5" /> : <MoonIcon className="h-5 w-5" />}
            </button>
            <NavLink
              to="/account"
              aria-label="Account"
              className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-soft text-xs font-medium text-teal"
            >
              {initials}
            </NavLink>
          </div>
        </header>
        <main className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">{children}</div>
        </main>
      </div>
    </div>
  );
}

function SidebarContent({
  primaryItems,
  libraryItems,
  adminItems,
  collapsedLabels = false,
  skipLogo = false,
  initials,
  email,
  theme,
  onToggleTheme,
  onLogout,
  isLoggingOut,
}: {
  primaryItems: NavItem[];
  libraryItems: NavItem[];
  adminItems: NavItem[];
  collapsedLabels?: boolean;
  skipLogo?: boolean;
  initials: string;
  email?: string;
  theme: "light" | "dark";
  onToggleTheme: () => void;
  onLogout: () => void;
  isLoggingOut: boolean;
}) {
  const labelClass = collapsedLabels ? "hidden lg:inline" : "";

  return (
    <div className="sidebar-scroll flex h-full flex-col overflow-y-auto">
      {!skipLogo && (
        <div className={`px-5 py-5 ${collapsedLabels ? "md:px-0 md:text-center lg:px-5 lg:text-left" : ""}`}>
          <span className="font-display text-base text-white">
            <span className={collapsedLabels ? "md:hidden lg:inline" : ""}>CoachFlow</span>
            <span className={collapsedLabels ? "hidden md:inline lg:hidden" : "hidden"} aria-hidden="true">
              CF
            </span>
          </span>
          <p
            className={`mt-1.5 text-[10px] uppercase tracking-wide text-sidebar-fg/60 ${
              collapsedLabels ? "hidden lg:block" : ""
            }`}
          >
            Executive Coaching
          </p>
        </div>
      )}

      <nav className="flex flex-1 flex-col gap-1 px-2 pt-2">
        <NavGroup items={primaryItems} labelClass={labelClass} collapsedLabels={collapsedLabels} />
        {libraryItems.length > 0 && (
          <>
            <GroupLabel className={labelClass}>Library</GroupLabel>
            <NavGroup items={libraryItems} labelClass={labelClass} collapsedLabels={collapsedLabels} />
          </>
        )}
        {adminItems.length > 0 && (
          <>
            <GroupLabel className={labelClass}>Admin</GroupLabel>
            <NavGroup items={adminItems} labelClass={labelClass} collapsedLabels={collapsedLabels} />
          </>
        )}
      </nav>

      <div className="mt-auto border-t border-white/10 px-2 py-3">
        <NavLink
          to="/account"
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
              isActive ? "bg-sidebar-accent/15 text-sidebar-accent font-medium" : "text-sidebar-fg/80 hover:bg-white/5"
            }`
          }
        >
          <SettingsIcon className="h-4 w-4 flex-shrink-0" />
          <span className={labelClass}>Account</span>
        </NavLink>
        <button
          type="button"
          onClick={onToggleTheme}
          className="mt-1 flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-sidebar-fg/80 transition-colors hover:bg-white/5"
        >
          {theme === "dark" ? <SunIcon className="h-4 w-4 flex-shrink-0" /> : <MoonIcon className="h-4 w-4 flex-shrink-0" />}
          <span className={labelClass}>{theme === "dark" ? "Light mode" : "Dark mode"}</span>
        </button>

        <div className={`mt-3 flex items-center gap-3 border-t border-white/10 px-3 pt-3 ${collapsedLabels ? "md:justify-center lg:justify-start" : ""}`}>
          <span className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-sidebar-accent/25 text-xs text-sidebar-accent">
            {initials}
          </span>
          <span className={`min-w-0 flex-1 truncate text-xs text-sidebar-fg/70 ${labelClass}`}>{email}</span>
          <button
            type="button"
            onClick={onLogout}
            disabled={isLoggingOut}
            aria-label="Log out"
            className={`flex-shrink-0 text-sidebar-fg/50 hover:text-sidebar-fg disabled:opacity-50 ${collapsedLabels ? "hidden lg:block" : ""}`}
          >
            <LogOutIcon className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

function GroupLabel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <p className={`px-3 pb-1 pt-4 text-[10px] font-semibold uppercase tracking-widest text-sidebar-fg/50 ${className}`}>
      {children}
    </p>
  );
}

function NavGroup({
  items,
  labelClass,
  collapsedLabels,
}: {
  items: NavItem[];
  labelClass: string;
  collapsedLabels: boolean;
}) {
  return (
    <>
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          title={collapsedLabels ? item.label : undefined}
          aria-label={item.label}
          className={({ isActive }) =>
            `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors ${
              collapsedLabels ? "md:justify-center lg:justify-start" : ""
            } ${isActive ? "bg-sidebar-accent/15 text-sidebar-accent font-medium" : "text-sidebar-fg/80 hover:bg-white/5"}`
          }
        >
          <item.icon className="h-4 w-4 flex-shrink-0" />
          <span className={labelClass}>{item.label}</span>
          {!!item.badge && (
            <span
              className={`ml-auto rounded-full bg-amber/20 px-1.5 py-0.5 text-[10px] tabular-nums text-amber ${
                collapsedLabels ? "hidden lg:inline" : ""
              }`}
            >
              {item.badge}
            </span>
          )}
        </NavLink>
      ))}
    </>
  );
}
