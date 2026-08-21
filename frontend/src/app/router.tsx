import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AccountPage } from "@/features/account/AccountPage";
import { AdminPanel } from "@/features/admin/AdminPanel";
import { ApprovalsInbox } from "@/features/approvals/ApprovalsInbox";
import { CalendarView } from "@/features/calendar/CalendarView";
import { ClientDetail } from "@/features/clients/ClientDetail";
import { ClientsDirectory } from "@/features/clients/ClientsDirectory";
import { LoginPage } from "@/features/auth/LoginPage";
import { MetricsDashboard } from "@/features/metrics/MetricsDashboard";
import { ScorecardView } from "@/features/scorecards/ScorecardView";
import { useRole } from "@/hooks/useRole";
import { useSession } from "@/hooks/useSession";

function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, loading } = useSession();
  if (loading) return null;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

/** Gates admin-only routes on the frontend as a UX nicety — the backend's
 * require_admin dependency is the actual authorization boundary (root
 * CLAUDE.md: "don't rely on the frontend hiding UI as the only gate"). */
function AdminRoute({ children }: { children: ReactNode }) {
  const { isAdmin, isLoading } = useRole();
  if (isLoading) return null;
  if (!isAdmin) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <CalendarView />
          </RequireAuth>
        }
      />
      <Route
        path="/approvals"
        element={
          <RequireAuth>
            <ApprovalsInbox />
          </RequireAuth>
        }
      />
      <Route
        path="/clients"
        element={
          <RequireAuth>
            <ClientsDirectory />
          </RequireAuth>
        }
      />
      <Route
        path="/clients/:clientId"
        element={
          <RequireAuth>
            <ClientDetail />
          </RequireAuth>
        }
      />
      <Route
        path="/sessions/:sessionId/scorecard"
        element={
          <RequireAuth>
            <ScorecardView />
          </RequireAuth>
        }
      />
      <Route
        path="/metrics"
        element={
          <RequireAuth>
            <MetricsDashboard />
          </RequireAuth>
        }
      />
      <Route
        path="/account"
        element={
          <RequireAuth>
            <AccountPage />
          </RequireAuth>
        }
      />
      <Route
        path="/admin"
        element={
          <RequireAuth>
            <AdminRoute>
              <AdminPanel />
            </AdminRoute>
          </RequireAuth>
        }
      />
    </Routes>
  );
}
