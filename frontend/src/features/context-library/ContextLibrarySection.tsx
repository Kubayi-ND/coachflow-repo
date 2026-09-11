import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Pill } from "@/components/ui/Pill";
import { Select } from "@/components/ui/Select";
import { Skeleton } from "@/components/ui/Skeleton";
import { Textarea } from "@/components/ui/Textarea";
import { useClients } from "@/hooks/useClients";
import {
  useContextLibraryEntries,
  useContextLibraryHistory,
  useCreateContextLibraryEntry,
  usePostContextLibraryVersion,
} from "@/hooks/useContextLibrary";
import type { Client, ContextLibraryEntry } from "@/types";

const entrySchema = z.object({
  title: z
    .string()
    .trim()
    .min(1, "Heading is required — describe what this entry covers so the AI can judge its relevance."),
  body: z.string().trim().min(1, "Body is required."),
});
type EntryFormValues = z.infer<typeof entrySchema>;

/** Editor for the Context Library entries — append-only: every save posts a
 * new version rather than overwriting, and the heading is required because
 * context_builder.py surfaces it above each entry's body in the assembled
 * prompt so the model can judge relevance among the entries it's given. */
export function ContextLibrarySection() {
  const { data: clients } = useClients();
  const [filterClientId, setFilterClientId] = useState("");
  const { data: entries, isLoading } = useContextLibraryEntries(filterClientId || undefined);
  const [expandedGroupId, setExpandedGroupId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate">Context Library</h2>
        <Button variant="secondary" size="sm" onClick={() => setCreating((c) => !c)}>
          {creating ? "Cancel" : "New entry"}
        </Button>
      </div>

      <div className="mb-4 flex items-center gap-2">
        <span className="text-xs text-slate">Filter</span>
        <Select value={filterClientId} onChange={(e) => setFilterClientId(e.target.value)}>
          <option value="">All entries</option>
          {clients?.map((client) => (
            <option key={client.id} value={client.id}>
              {client.name}
            </option>
          ))}
        </Select>
      </div>

      {creating && <NewEntryForm clients={clients ?? []} onDone={() => setCreating(false)} />}

      {isLoading ? (
        <RowsSkeleton count={3} />
      ) : entries && entries.length > 0 ? (
        <div className="space-y-2">
          {entries.map((entry) => (
            <ContextLibraryRow
              key={entry.entryGroupId}
              entry={entry}
              clientName={clients?.find((c) => c.id === entry.clientId)?.name}
              expanded={expandedGroupId === entry.entryGroupId}
              onToggleHistory={() =>
                setExpandedGroupId((prev) => (prev === entry.entryGroupId ? null : entry.entryGroupId))
              }
            />
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate">No Context Library entries yet.</p>
      )}
    </section>
  );
}

function NewEntryForm({ clients, onDone }: { clients: Client[]; onDone: () => void }) {
  const [clientId, setClientId] = useState("");
  const createEntry = useCreateContextLibraryEntry();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<EntryFormValues>({ resolver: zodResolver(entrySchema) });

  const onSubmit = handleSubmit((values) => {
    createEntry.mutate(
      { clientId: clientId || null, title: values.title, body: values.body },
      {
        onSuccess: () => {
          reset();
          setClientId("");
          onDone();
        },
      }
    );
  });

  return (
    <form onSubmit={onSubmit} className="mb-4 space-y-3 rounded-xl border border-border bg-surface p-4 shadow-card">
      <div>
        <label className="mb-1 block text-xs text-slate">Scope</label>
        <Select value={clientId} onChange={(e) => setClientId(e.target.value)}>
          <option value="">Org-wide (all clients)</option>
          {clients.map((client) => (
            <option key={client.id} value={client.id}>
              {client.name}
            </option>
          ))}
        </Select>
      </div>
      <div>
        <label className="mb-1 block text-xs text-slate">Heading</label>
        <Input placeholder="e.g. 'GROW Model — Goal-Setting Techniques'" error={!!errors.title} {...register("title")} />
        {errors.title && <p className="mt-1 text-xs text-amber">{errors.title.message}</p>}
      </div>
      <div>
        <label className="mb-1 block text-xs text-slate">Body</label>
        <Textarea rows={6} error={!!errors.body} {...register("body")} />
        {errors.body && <p className="mt-1 text-xs text-amber">{errors.body.message}</p>}
      </div>
      <Button type="submit" isLoading={createEntry.isPending}>
        Create entry
      </Button>
    </form>
  );
}

function ContextLibraryRow({
  entry,
  clientName,
  expanded,
  onToggleHistory,
}: {
  entry: ContextLibraryEntry;
  clientName?: string;
  expanded: boolean;
  onToggleHistory: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const { data: history } = useContextLibraryHistory(expanded ? entry.entryGroupId : null);

  return (
    <div className="rounded-xl border border-border bg-surface px-4 py-3 shadow-card">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-ink">{entry.title}</p>
          <p className="mt-1 text-xs text-slate">{entry.body}</p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Pill tone={entry.clientId ? "neutral" : "teal"}>{entry.clientId ? (clientName ?? "Client") : "Org-wide"}</Pill>
          <Pill>v{entry.version}</Pill>
        </div>
      </div>
      <div className="mt-2 flex gap-3 text-xs">
        <button className="text-teal hover:underline" onClick={() => setEditing((e) => !e)}>
          {editing ? "Cancel" : "Post new version"}
        </button>
        <button className="text-slate hover:underline" onClick={onToggleHistory}>
          {expanded ? "Hide history" : "View history"}
        </button>
      </div>

      {editing && (
        <PostVersionForm
          entryGroupId={entry.entryGroupId}
          initialTitle={entry.title}
          initialBody={entry.body}
          onDone={() => setEditing(false)}
        />
      )}

      {expanded && (
        <div className="mt-3 space-y-1 border-t border-border pt-3">
          {history?.map((version) => (
            <div key={version.id} className="text-xs text-slate">
              <span className="tabular-nums">v{version.version}</span> — {version.title}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PostVersionForm({
  entryGroupId,
  initialTitle,
  initialBody,
  onDone,
}: {
  entryGroupId: string;
  initialTitle: string;
  initialBody: string;
  onDone: () => void;
}) {
  const postVersion = usePostContextLibraryVersion();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<EntryFormValues>({
    resolver: zodResolver(entrySchema),
    defaultValues: { title: initialTitle, body: initialBody },
  });

  const onSubmit = handleSubmit((values) => {
    postVersion.mutate({ entryGroupId, title: values.title, body: values.body }, { onSuccess: onDone });
  });

  return (
    <form onSubmit={onSubmit} className="mt-3 space-y-2 border-t border-border pt-3">
      <Input error={!!errors.title} {...register("title")} />
      {errors.title && <p className="text-xs text-amber">{errors.title.message}</p>}
      <Textarea rows={6} error={!!errors.body} {...register("body")} />
      {errors.body && <p className="text-xs text-amber">{errors.body.message}</p>}
      <Button type="submit" variant="secondary" isLoading={postVersion.isPending}>
        Post version
      </Button>
    </form>
  );
}

function RowsSkeleton({ count }: { count: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex items-center justify-between rounded-xl border border-border px-4 py-3">
          <div className="space-y-2">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-3 w-64" />
          </div>
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>
      ))}
    </div>
  );
}
