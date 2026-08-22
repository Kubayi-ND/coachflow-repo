import type { ReactNode } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { AccountPage } from "@/features/account/AccountPage";
import { ImportPage } from "@/features/admin/ImportPage";
import { UsersPage } from "@/features/admin/UsersPage";
import { ApprovalsInbox } from "@/features/approvals/ApprovalsInbox";
import { ForgotPasswordPage } from "@/features/auth/ForgotPasswordPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { SetPasswordPage } from "@/features/auth/SetPasswordPage";
import { CalendarView } from "@/features/calendar/CalendarView";
import { ClientDetail } from "@/features/clients/ClientDetail";
import { ClientsDirectory } from "@/features/clients/ClientsDirectory";
import { ContextLibraryPage } from "@/features/context-library/ContextLibraryPage";
import { ScorecardView } from "@/features/scorecards/ScorecardView";
import { useRole } from "@/hooks/useRole";
import { useSession } from "@/hooks/useSession";

function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, loading } = useSession();
  const { mustResetPassword, isLoading: roleLoading } = useRole();
  const location = useLocation();

  if (loading) return null;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  // Admin-provisioned accounts (temporary password) must set their own
  // password before touching anything else in the dashboard.
  if (!roleLoading && mustResetPassword && location.pathname !== "/set-password") {
    return <Navigate to="/set-password" replace />;
  }
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

function CoachLibraryRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useRole();
  if (isLoading) return null;
  if (user?.role !== "general" && user?.role !== "admin") return <Navigate to="/" replace />;
  return <>{children}</>;
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/set-password" element={<SetPasswordPage />} />
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
        path="/account"
        element={
          <RequireAuth>
            <AccountPage />
          </RequireAuth>
        }
      />
      <Route
        path="/context-library"
        element={
          <RequireAuth>
            <CoachLibraryRoute>
              <ContextLibraryPage />
            </CoachLibraryRoute>
          </RequireAuth>
        }
      />
      <Route
        path="/admin/users"
        element={
          <RequireAuth>
            <AdminRoute>
              <UsersPage />
            </AdminRoute>
          </RequireAuth>
        }
      />
      <Route
        path="/admin/imports"
        element={
          <RequireAuth>
            <AdminRoute>
              <ImportPage />
            </AdminRoute>
          </RequireAuth>
        }
      />
    </Routes>
  );
}
