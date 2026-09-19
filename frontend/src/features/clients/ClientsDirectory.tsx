import { useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { Pill } from "@/components/ui/Pill";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { ChevronRightIcon, SearchIcon } from "@/components/ui/icons";
import { useClients, useCreateClient } from "@/hooks/useClients";
import { SESSION_TYPE_IDS, SESSION_TYPES } from "@/types";
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
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<SessionTypeId | null>(null);

  const needle = query.trim().toLowerCase();
  const visibleClients = (clients ?? []).filter(
    (client) =>
      (!needle || client.name.toLowerCase().includes(needle) || client.email.toLowerCase().includes(needle)) &&
      (!typeFilter || client.sessionTypes.includes(typeFilter))
  );
  const filtering = needle !== "" || typeFilter !== null;

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

      {(clients?.length ?? 0) > 0 && (
        <div className="space-y-3">
          <label className="relative block">
            <span className="sr-only">Search clients</span>
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate" />
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search by name or email"
              className="h-9 w-full rounded-lg border border-border bg-surface pl-9 pr-3 text-sm text-ink placeholder:text-slate focus:border-teal/50 focus:outline-none focus:ring-2 focus:ring-teal/20"
            />
          </label>
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by session type">
            {SESSION_TYPE_IDS.map((id) => (
              <button
                key={id}
                type="button"
                aria-pressed={typeFilter === id}
                onClick={() => setTypeFilter((current) => (current === id ? null : id))}
                className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                  typeFilter === id
                    ? "border-teal bg-teal-soft text-teal"
                    : "border-border text-slate hover:border-teal/40 hover:text-ink"
                }`}
              >
                {SESSION_TYPES[id].label}
              </button>
            ))}
          </div>
        </div>
      )}

      {isLoading && <ClientsDirectorySkeleton />}
      {!isLoading && (clients?.length ?? 0) === 0 && !creating && (
        <p className="rounded-xl border border-dashed border-border px-4 py-6 text-center text-sm text-slate">
          No clients yet. Use Add client to create your first one.
        </p>
      )}
      {filtering && visibleClients.length === 0 && (
        <p className="rounded-xl border border-dashed border-border px-4 py-6 text-center text-sm text-slate">
          No clients match.{" "}
          <button
            type="button"
            className="font-medium text-teal hover:underline"
            onClick={() => {
              setQuery("");
              setTypeFilter(null);
            }}
          >
            Clear filters
          </button>
        </p>
      )}
      <div
        className={`overflow-hidden rounded-xl border border-border bg-surface shadow-card ${visibleClients.length === 0 ? "hidden" : ""}`}
      >
        <ul className="divide-y divide-border">
          {visibleClients.map((client) => (
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
