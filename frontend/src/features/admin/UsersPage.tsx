import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { useUsers } from "@/hooks/useUsers";
import type { CreateUserResult } from "@/types";

import { CreateUserForm } from "./CreateUserForm";
import { UsersTable } from "./UsersTable";

/** Admin-only: add, suspend, reactivate, and (soft-)delete app users. A
 * created user gets a generated one-time password shown here exactly once —
 * hand it to the coach directly, they're forced to set their own on first
 * login. */
export function UsersPage() {
  const { data: users, isLoading } = useUsers();
  const [creating, setCreating] = useState(false);
  const [newCredentials, setNewCredentials] = useState<CreateUserResult | null>(null);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-end">
        <Button
          variant="secondary"
          onClick={() => {
            setNewCredentials(null);
            setCreating((c) => !c);
          }}
        >
          {creating ? "Cancel" : "Add user"}
        </Button>
      </div>

      {creating && (
        <div className="rounded-xl border border-border bg-surface p-4 shadow-card">
          <CreateUserForm
            onDone={(result) => {
              setCreating(false);
              setNewCredentials(result);
            }}
          />
        </div>
      )}

      {newCredentials && (
        <NewCredentialsPanel result={newCredentials} onDismiss={() => setNewCredentials(null)} />
      )}

      {isLoading ? <UsersTableSkeleton /> : <UsersTable users={users ?? []} />}
    </div>
  );
}

function NewCredentialsPanel({ result, onDismiss }: { result: CreateUserResult; onDismiss: () => void }) {
  const toast = useToast();

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(result.temporaryPassword);
      toast.show("Password copied");
    } catch {
      toast.show("Couldn't copy — select and copy it manually.", "error");
    }
  }

  return (
    <div className="space-y-2 rounded-xl border border-amber/30 bg-amber/5 px-4 py-3">
      <p className="text-sm text-ink">
        Account created for <span className="font-medium">{result.user.email}</span>. This
        one-time password is shown once — copy it now and share it with the coach directly (it
        cannot be retrieved again). They'll be required to set their own password on first login.
      </p>
      <div className="flex items-center gap-2">
        <code className="rounded-md bg-surface px-2 py-1 text-sm text-ink">{result.temporaryPassword}</code>
        <Button variant="secondary" onClick={handleCopy}>
          Copy
        </Button>
        <Button variant="secondary" onClick={onDismiss}>
          Done
        </Button>
      </div>
    </div>
  );
}

function UsersTableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="flex items-center justify-between rounded-xl border border-border px-4 py-3">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-5 w-16 rounded-full" />
          <Skeleton className="h-8 w-40" />
        </div>
      ))}
    </div>
  );
}
