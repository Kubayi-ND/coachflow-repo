import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Pill } from "@/components/ui/Pill";
import { Select } from "@/components/ui/Select";
import { useToast } from "@/components/ui/Toast";
import { useClients } from "@/hooks/useClients";
import { useImportJobItems, useImportJobs, useResolveImportItem, useStartImport } from "@/hooks/useImports";
import type { ImportItem, ImportJobStatus, ImportSource, TenantId } from "@/types";

const SOURCES: { id: ImportSource; label: string; hint: string }[] = [
  { id: "calendar", label: "Calendar events", hint: "Folder of exported calendar-event JSON files" },
  { id: "context_library", label: "GROW context library", hint: "ICF/GROW reference docs — org-wide" },
  { id: "client_notes", label: "Client notes", hint: "One subfolder per client" },
  { id: "transcripts", label: "Transcripts", hint: "One subfolder per client" },
];

const JOB_STATUS_TONE: Record<ImportJobStatus, "neutral" | "teal" | "amber"> = {
  running: "amber",
  completed: "teal",
  failed: "amber",
};

/** Admin-only one-time Drive backfill for the four pre-existing folders a
 * tenant may have accumulated before CoachFlow existed. Ongoing calendar
 * sync and transcript intake keep using the already-built live paths — this
 * page only needs to run once per tenant per source. */
export function ImportPage() {
  const [tenantId, setTenantId] = useState<TenantId>("tenant_a");
  const [folderIds, setFolderIds] = useState<Record<ImportSource, string>>({
    calendar: "",
    context_library: "",
    client_notes: "",
    transcripts: "",
  });
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);

  const { data: jobs, isLoading } = useImportJobs(tenantId);
  const startImport = useStartImport();
  const toast = useToast();

  function handleStart(source: ImportSource) {
    const folderId = folderIds[source].trim();
    if (!folderId) {
      toast.show("Paste a Drive folder id first", "error");
      return;
    }
    startImport.mutate(
      { tenantId, source, folderId },
      {
        onSuccess: () => toast.show("Import started"),
        onError: () => toast.show("Couldn't start the import", "error"),
      }
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl">Import</h1>
        <Select value={tenantId} onChange={(e) => setTenantId(e.target.value as TenantId)}>
          <option value="tenant_a">Tenant A</option>
          <option value="tenant_b">Tenant B</option>
        </Select>
      </div>
      <p className="text-sm text-slate">
        One-time backfill of pre-existing Drive folders into CoachFlow. Ongoing calendar sync and transcript
        intake keep using the live paths — each source below only needs to run once per tenant.
      </p>

      <section className="space-y-3">
        {SOURCES.map((source) => (
          <div key={source.id} className="flex items-center gap-3 rounded-md border border-slate/15 px-4 py-3">
            <div className="flex-1">
              <p className="text-sm font-medium">{source.label}</p>
              <p className="text-xs text-slate">{source.hint}</p>
            </div>
            <Input
              placeholder="Drive folder id"
              className="max-w-xs"
              value={folderIds[source.id]}
              onChange={(e) => setFolderIds((prev) => ({ ...prev, [source.id]: e.target.value }))}
            />
            <Button variant="secondary" isLoading={startImport.isPending} onClick={() => handleStart(source.id)}>
              Start import
            </Button>
          </div>
        ))}
      </section>

      <section>
        <h2 className="text-lg mb-2">Import jobs</h2>
        {isLoading && <p className="text-sm text-slate">Loading…</p>}
        <ul className="space-y-2">
          {(jobs ?? []).map((job) => (
            <li key={job.id} className="rounded-md border border-slate/15 px-4 py-3">
              <button
                className="flex w-full items-center justify-between text-left"
                onClick={() => setExpandedJobId((id) => (id === job.id ? null : job.id))}
              >
                <div>
                  <p className="text-sm">{SOURCES.find((s) => s.id === job.source)?.label ?? job.source}</p>
                  <p className="text-xs text-slate tabular-nums">
                    {job.itemsSucceeded} succeeded · {job.itemsFailed} failed · {job.itemsTotal} total
                  </p>
                </div>
                <Pill tone={JOB_STATUS_TONE[job.status]}>{job.status}</Pill>
              </button>
              {job.errorMessage && <p className="mt-2 text-xs text-amber">{job.errorMessage}</p>}
              {expandedJobId === job.id && <ImportJobItems jobId={job.id} />}
            </li>
          ))}
          {!isLoading && (jobs ?? []).length === 0 && <p className="text-sm text-slate">No imports yet.</p>}
        </ul>
      </section>
    </div>
  );
}

function ImportJobItems({ jobId }: { jobId: string }) {
  const { data: items } = useImportJobItems(jobId);
  const { data: clients } = useClients();
  const resolveItem = useResolveImportItem();
  const toast = useToast();

  if (!items) return null;

  const unmatched = items.filter((item) => item.status === "unmatched_client");
  const failed = items.filter((item) => item.status === "failed");

  function handleAssign(item: ImportItem, clientId: string) {
    resolveItem.mutate(
      { itemId: item.id, clientId },
      {
        onSuccess: () => toast.show("Assigned"),
        onError: () => toast.show("Couldn't assign a client", "error"),
      }
    );
  }

  return (
    <div className="mt-3 space-y-3 border-t border-slate/15 pt-3">
      {unmatched.length > 0 && (
        <div>
          <p className="text-xs font-medium text-slate mb-1">Needs a client ({unmatched.length})</p>
          <ul className="space-y-2">
            {unmatched.map((item) => (
              <li
                key={item.id}
                className="flex items-center justify-between rounded-md border border-amber/40 bg-amber/5 px-3 py-2"
              >
                <span className="text-sm">{item.fileName}</span>
                <Select
                  className="text-sm py-1"
                  defaultValue=""
                  onChange={(e) => e.target.value && handleAssign(item, e.target.value)}
                >
                  <option value="" disabled>
                    Assign client
                  </option>
                  {(clients ?? []).map((client) => (
                    <option key={client.id} value={client.id}>
                      {client.name}
                    </option>
                  ))}
                </Select>
              </li>
            ))}
          </ul>
        </div>
      )}
      {failed.length > 0 && (
        <div>
          <p className="text-xs font-medium text-slate mb-1">Failed ({failed.length})</p>
          <ul className="space-y-1">
            {failed.map((item) => (
              <li key={item.id} className="text-xs text-slate">
                {item.fileName} — {item.errorMessage}
              </li>
            ))}
          </ul>
        </div>
      )}
      {unmatched.length === 0 && failed.length === 0 && (
        <p className="text-xs text-slate">Every file in this run imported cleanly.</p>
      )}
    </div>
  );
}
