import { Link } from "react-router-dom";

import { Pill } from "@/components/ui/Pill";
import { Skeleton } from "@/components/ui/Skeleton";
import { ChevronRightIcon } from "@/components/ui/icons";
import { useClients } from "@/hooks/useClients";

/** Directory across both tenants (frontend/CLAUDE.md). */
export function ClientsDirectory() {
  const { data: clients, isLoading } = useClients();

  return (
    <div>
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
