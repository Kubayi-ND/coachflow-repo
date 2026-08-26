import { Button } from "@/components/ui/Button";
import { Pill } from "@/components/ui/Pill";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { useClients } from "@/hooks/useClients";
import { useLogout } from "@/hooks/useLogout";
import { useRole } from "@/hooks/useRole";

/** Account management — a read-only identity summary plus sign-out. No
 * profile editing here: there is no PATCH /api/users/me endpoint. */
export function AccountPage() {
  const { user, isAdmin, isLoading } = useRole();
  const logout = useLogout();
  const toast = useToast();

  if (isLoading || !user) return <AccountPageSkeleton />;

  async function handleLogout() {
    try {
      await logout.mutateAsync();
    } catch {
      toast.show("Failed to log out", "error");
    }
  }

  return (
    <div className="max-w-lg space-y-6">
      <div className="rounded-xl border border-border bg-surface p-5 shadow-card space-y-4">
        <div>
          <p className="text-xs text-slate">Email</p>
          <p className="mt-1 text-sm text-ink">{user.email}</p>
        </div>
        <div>
          <p className="mb-1 text-xs text-slate">Role</p>
          <Pill tone={isAdmin ? "teal" : "neutral"}>{isAdmin ? "Admin" : "Coach"}</Pill>
        </div>
      </div>

      {!isAdmin && <AssignedClients />}

      <Button variant="secondary" onClick={handleLogout} isLoading={logout.isPending}>
        Log out
      </Button>
    </div>
  );
}

/** General-role users only. GET /api/clients is already scoped to a
 * coach's assigned clients server-side (root CLAUDE.md "Roles"). */
function AssignedClients() {
  const { data: clients, isLoading } = useClients();

  return (
    <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
      <p className="mb-2 text-xs text-slate">Assigned clients</p>
      {isLoading && (
        <div className="space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-28" />
        </div>
      )}
      {clients && clients.length === 0 && <p className="text-sm text-slate">No clients assigned yet.</p>}
      {clients && clients.length > 0 && (
        <ul className="space-y-1 text-sm text-ink">
          {clients.map((client) => (
            <li key={client.id}>{client.name}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function AccountPageSkeleton() {
  return (
    <div className="max-w-lg space-y-6">
      <div className="rounded-xl border border-border bg-surface p-5 shadow-card space-y-4">
        <div>
          <Skeleton className="h-3 w-12 mb-2" />
          <Skeleton className="h-4 w-40" />
        </div>
        <div>
          <Skeleton className="h-3 w-10 mb-2" />
          <Skeleton className="h-5 w-16 rounded-full" />
        </div>
      </div>
      <Skeleton className="h-9 w-24" />
    </div>
  );
}
