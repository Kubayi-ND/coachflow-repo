import { Link } from "react-router-dom";

import { Pill } from "@/components/ui/Pill";
import { Skeleton } from "@/components/ui/Skeleton";
import { useClients } from "@/hooks/useClients";

/** Directory across both tenants (frontend/CLAUDE.md). */
export function ClientsDirectory() {
  const { data: clients, isLoading } = useClients();

  return (
    <div>
      <h1 className="text-2xl mb-4">Clients &amp; companies</h1>
      {isLoading && <ClientsDirectorySkeleton />}
      <ul className="space-y-2">
        {clients?.map((client) => (
          <li key={client.id}>
            <Link
              to={`/clients/${client.id}`}
              className="flex items-center justify-between rounded-md border border-slate/15 px-4 py-3 hover:border-teal/50"
            >
              <span>{client.name}</span>
              <Pill>{client.tenantId === "tenant_a" ? "Tenant A" : "Tenant B"}</Pill>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ClientsDirectorySkeleton() {
  return (
    <ul className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <li key={i} className="flex items-center justify-between rounded-md border border-slate/15 px-4 py-3">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-5 w-20 rounded-full" />
        </li>
      ))}
    </ul>
  );
}
