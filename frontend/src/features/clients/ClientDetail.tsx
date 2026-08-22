import { useParams } from "react-router-dom";

import { Pill } from "@/components/ui/Pill";
import { Skeleton } from "@/components/ui/Skeleton";
import { useClients } from "@/hooks/useClients";
import { useContextLibraryEntries } from "@/hooks/useContextLibrary";
import { SESSION_TYPES } from "@/types";

/** Links out to the client's Drive folder structure (Transcripts / Context /
 * Evaluations) and shows their Context Library entries and session-type
 * configuration (frontend/CLAUDE.md). */
export function ClientDetail() {
  const { clientId } = useParams<{ clientId: string }>();
  const { data: clients } = useClients();
  const client = clients?.find((c) => c.id === clientId);
  const { data: contextEntries } = useContextLibraryEntries(clientId);

  if (!client) return <ClientDetailSkeleton />;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl">{client.name}</h1>

      {client.driveFolderId && (
        <a
          href={`https://drive.google.com/drive/folders/${client.driveFolderId}`}
          target="_blank"
          rel="noreferrer"
          className="text-teal text-sm underline"
        >
          Open Drive folder (Transcripts / Context / Evaluations)
        </a>
      )}

      <section>
        <h2 className="text-lg mb-2">Session types</h2>
        <ul className="flex gap-2 flex-wrap">
          {client.sessionTypes.map((type) => (
            <li key={type}>
              <Pill tone="teal">{SESSION_TYPES[type].label}</Pill>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="text-lg mb-2">Context Library</h2>
        {contextEntries && contextEntries.length === 0 && (
          <p className="text-sm text-slate">No Context Library entries for this client yet.</p>
        )}
        <ul className="space-y-2">
          {(contextEntries ?? []).map((entry) => (
            <li key={entry.id} className="rounded-md border border-slate/15 px-4 py-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium">{entry.title}</p>
                {entry.clientId === null && <Pill tone="teal">Org-wide</Pill>}
              </div>
              <p className="text-sm text-slate whitespace-pre-wrap">{entry.body}</p>
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
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-4 w-64" />
      <section>
        <h2 className="text-lg mb-2">Session types</h2>
        <ul className="flex gap-2 flex-wrap">
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
