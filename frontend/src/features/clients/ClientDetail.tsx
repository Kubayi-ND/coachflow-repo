import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { Pill } from "@/components/ui/Pill";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatTile } from "@/components/ui/StatTile";
import { useToast } from "@/components/ui/Toast";
import { BookIcon, CalendarIcon, ExternalLinkIcon } from "@/components/ui/icons";
import { useClients, useDeleteClient, useUpdateClient } from "@/hooks/useClients";
import { useContextLibraryEntries } from "@/hooks/useContextLibrary";
import { SESSION_TYPES } from "@/types";
import type { SessionTypeId } from "@/types";

import { ClientForm } from "./ClientForm";

/** Links out to the client's Drive folder structure (Transcripts / Context /
 * Evaluations) and shows their Context Library entries and session-type
 * configuration (frontend/CLAUDE.md). The assigned coach (or an admin) can
 * edit or remove the client from here. */
export function ClientDetail() {
  const { clientId } = useParams<{ clientId: string }>();
  const navigate = useNavigate();
  const { data: clients } = useClients();
  const client = clients?.find((c) => c.id === clientId);
  const { data: contextEntries } = useContextLibraryEntries(clientId);
  const updateClient = useUpdateClient();
  const deleteClient = useDeleteClient();
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  if (!client) return <ClientDetailSkeleton />;

  async function handleDelete() {
    if (!client) return;
    try {
      await deleteClient.mutateAsync(client.id);
      toast.show(`${client.name} removed`);
      navigate("/clients");
    } catch {
      toast.show("Failed to remove client", "error");
      setConfirmingDelete(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border bg-surface p-5 shadow-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <h1 className="font-display text-2xl text-ink">{client.name}</h1>
            <Pill>{client.tenantId === "tenant_a" ? "Tenant A" : "Tenant B"}</Pill>
          </div>
          <div className="flex items-center gap-3">
            {client.driveFolderId && (
              <a
                href={`https://drive.google.com/drive/folders/${client.driveFolderId}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-sm font-medium text-teal hover:text-teal/70"
              >
                Open Drive folder
                <ExternalLinkIcon className="h-3.5 w-3.5" />
              </a>
            )}
            <Button variant="secondary" onClick={() => setEditing((e) => !e)}>
              {editing ? "Cancel" : "Edit"}
            </Button>
            {confirmingDelete ? (
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate">Delete {client.name}?</span>
                <Button variant="danger" onClick={handleDelete} isLoading={deleteClient.isPending}>
                  Confirm
                </Button>
                <Button variant="secondary" onClick={() => setConfirmingDelete(false)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <Button variant="danger" onClick={() => setConfirmingDelete(true)}>
                Delete
              </Button>
            )}
          </div>
        </div>

        {editing && (
          <div className="mt-4 border-t border-border pt-4">
            <ClientForm
              submitLabel="Save changes"
              isPending={updateClient.isPending}
              defaultValues={{
                name: client.name,
                email: client.email,
                tenantId: client.tenantId,
                sessionTypes: client.sessionTypes,
              }}
              onCancel={() => setEditing(false)}
              onSubmit={(values) => {
                updateClient.mutate(
                  {
                    clientId: client.id,
                    input: {
                      name: values.name,
                      email: values.email,
                      tenantId: values.tenantId,
                      sessionTypes: values.sessionTypes as SessionTypeId[],
                    },
                  },
                  {
                    onSuccess: () => setEditing(false),
                    onError: () => toast.show("Failed to update client.", "error"),
                  }
                );
              }}
            />
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-2">
        <StatTile label="Session types configured" value={client.sessionTypes.length} icon={<CalendarIcon className="h-5 w-5" />} />
        <StatTile label="Context entries" value={contextEntries?.length ?? 0} icon={<BookIcon className="h-5 w-5" />} tone="teal" />
      </div>

      <section className="rounded-xl border border-border bg-surface p-5 shadow-card">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate">Session types</h2>
        <ul className="flex flex-wrap gap-2">
          {client.sessionTypes.map((type) => (
            <li key={type}>
              <Pill tone="teal">{SESSION_TYPES[type].label}</Pill>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-border bg-surface p-5 shadow-card">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate">Context Library</h2>
        {contextEntries && contextEntries.length === 0 && (
          <p className="text-sm text-slate">No Context Library entries for this client yet.</p>
        )}
        <ul className="space-y-2">
          {(contextEntries ?? []).map((entry) => (
            <li key={entry.id} className="rounded-lg border border-border bg-surface-2 px-4 py-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-ink">{entry.title}</p>
                {entry.clientId === null && <Pill tone="teal">Org-wide</Pill>}
              </div>
              <p className="mt-1 whitespace-pre-wrap text-sm text-slate">{entry.body}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function ClientDetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-border bg-surface p-5 shadow-card space-y-2">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-64" />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Skeleton className="h-24 rounded-xl" />
        <Skeleton className="h-24 rounded-xl" />
      </div>
      <section className="rounded-xl border border-border bg-surface p-5 shadow-card">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate">Session types</h2>
        <ul className="flex flex-wrap gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <li key={i}>
              <Skeleton className="h-6 w-28 rounded-full" />
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
