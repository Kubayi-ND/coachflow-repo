import { useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { Pill } from "@/components/ui/Pill";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { ChevronRightIcon } from "@/components/ui/icons";
import { useClients, useCreateClient } from "@/hooks/useClients";
import type { SessionTypeId } from "@/types";

import { ClientForm } from "./ClientForm";

/** Directory across both tenants (frontend/CLAUDE.md). A coach creates and
 * manages their own clients here — self-assigned on creation, not assigned
 * by an admin (see the plan's Context section for why this diverges from
 * the doc as originally written). */
export function ClientsDirectory() {
  const { data: clients, isLoading } = useClients();
  const createClient = useCreateClient();
  const toast = useToast();
  const [creating, setCreating] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-end">
        <Button variant="secondary" onClick={() => setCreating((c) => !c)}>
          {creating ? "Cancel" : "Add client"}
        </Button>
      </div>

      {creating && (
        <div className="rounded-xl border border-border bg-surface p-4 shadow-card">
          <ClientForm
            submitLabel="Add client"
            showContext
            isPending={createClient.isPending}
            onCancel={() => setCreating(false)}
            onSubmit={(values) => {
              createClient.mutate(
                {
                  name: values.name,
                  email: values.email,
                  tenantId: values.tenantId,
                  sessionTypes: values.sessionTypes as SessionTypeId[],
                  context: values.context || undefined,
                },
                {
                  onSuccess: () => setCreating(false),
                  onError: () => toast.show("Failed to create client.", "error"),
                }
              );
            }}
          />
        </div>
      )}

      {isLoading && <ClientsDirectorySkeleton />}
      <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-card">
        <ul className="divide-y divide-border">
          {clients?.map((client) => (
            <li key={client.id}>
              <Link
                to={`/clients/${client.id}`}
                className="flex items-center gap-3 px-4 py-3 transition-colors hover:bg-surface-2"
              >
                <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-teal-soft text-xs font-medium text-teal">
                  {initialsFor(client.name)}
                </span>
                <span className="min-w-0 flex-1 truncate text-sm font-medium text-ink">{client.name}</span>
                <Pill>{client.tenantId === "tenant_a" ? "Tenant A" : "Tenant B"}</Pill>
                <ChevronRightIcon className="h-4 w-4 flex-shrink-0 text-slate" />
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function initialsFor(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts[1]?.[0] ?? "")).toUpperCase() || "?";
}

function ClientsDirectorySkeleton() {
  return (
    <div className="mb-4 divide-y divide-border overflow-hidden rounded-xl border border-border">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 px-4 py-3">
          <Skeleton className="h-9 w-9 rounded-full" />
          <Skeleton className="h-4 w-40" />
          <Skeleton className="ml-auto h-5 w-20 rounded-full" />
        </div>
      ))}
    </div>
  );
}
