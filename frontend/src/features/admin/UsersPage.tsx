import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { useUsers } from "@/hooks/useUsers";

import { CreateUserForm } from "./CreateUserForm";
import { UsersTable } from "./UsersTable";

/** Admin-only: add, suspend, reactivate, and (soft-)delete app users. A
 * created user gets a Supabase-sent email to set their own account
 * password — there's no password field anywhere in this admin flow. */
export function UsersPage() {
  const { data: users, isLoading } = useUsers();
  const [creating, setCreating] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl">Users</h1>
        <Button variant="secondary" onClick={() => setCreating((c) => !c)}>
          {creating ? "Cancel" : "Add user"}
        </Button>
      </div>

      {creating && <CreateUserForm onDone={() => setCreating(false)} />}

      {isLoading ? <UsersTableSkeleton /> : <UsersTable users={users ?? []} />}
    </div>
  );
}

function UsersTableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex items-center justify-between rounded-md border border-slate/15 px-4 py-3">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-8 w-40" />
        </div>
      ))}
    </div>
  );
}
