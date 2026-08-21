import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Pill } from "@/components/ui/Pill";
import { Skeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/components/ui/Toast";
import { useApproveDraft, useDrafts, useRejectDraft } from "@/hooks/useDrafts";
import type { AiDraft, DraftType, TenantId } from "@/types";

const DRAFT_TYPE_LABEL: Record<DraftType, string> = {
  reminder: "Reminder",
  summary: "Summary",
  questionnaire: "Questionnaire",
  prep_email: "Prep email",
};

/** The core loop. Never auto-refresh-away an item the coach has started
 * editing — edited state is local to each row and only cleared on an
 * explicit action (frontend/CLAUDE.md). */
export function ApprovalsInbox() {
  const { data: drafts, isLoading } = useDrafts();

  return (
    <div>
      <h1 className="text-2xl mb-4">Approvals</h1>
      {isLoading && <ApprovalsSkeleton />}
      {drafts && drafts.length === 0 && <p className="text-slate">Nothing pending — inbox is clear.</p>}
      <div className="space-y-4">
        {drafts?.map((draft) => (
          <DraftRow key={draft.id} draft={draft} />
        ))}
      </div>
    </div>
  );
}

function DraftRow({ draft }: { draft: AiDraft }) {
  const [editedBody, setEditedBody] = useState<string | null>(null);
  const [rejecting, setRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const approveDraft = useApproveDraft();
  const rejectDraft = useRejectDraft();
  const toast = useToast();

  const bodyValue = editedBody ?? draft.body;

  async function handleApprove() {
    try {
      await approveDraft.mutateAsync({ draftId: draft.id, editedBody: editedBody ?? undefined });
      toast.show("Sent");
    } catch {
      toast.show("Failed to send", "error");
    }
  }

  async function handleReject() {
    if (!rejectReason.trim()) return;
    try {
      await rejectDraft.mutateAsync({ draftId: draft.id, reason: rejectReason });
      toast.show("Draft rejected");
    } catch {
      toast.show("Failed to reject", "error");
    }
  }

  return (
    <div className="rounded-lg border border-slate/20 p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Pill tone="teal">{DRAFT_TYPE_LABEL[draft.draftType]}</Pill>
        <TenantPill tenantId={draft.tenantId} />
      </div>
      <textarea
        className="w-full min-h-32 rounded-md border border-slate/30 bg-transparent p-3 text-sm"
        value={bodyValue}
        onChange={(e) => setEditedBody(e.target.value)}
      />
      {rejecting ? (
        <div className="flex gap-2">
          <input
            className="flex-1 rounded-md border border-slate/30 bg-transparent px-3 py-2 text-sm"
            placeholder="Reason for rejection"
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
          />
          <Button variant="danger" onClick={handleReject} disabled={rejectDraft.isPending}>
            Confirm reject
          </Button>
          <Button variant="secondary" onClick={() => setRejecting(false)}>
            Cancel
          </Button>
        </div>
      ) : (
        <div className="flex gap-2">
          <Button onClick={handleApprove} disabled={approveDraft.isPending}>
            {editedBody !== null ? "Edit then approve" : "Approve & send"}
          </Button>
          <Button variant="danger" onClick={() => setRejecting(true)}>
            Reject
          </Button>
        </div>
      )}
    </div>
  );
}

function ApprovalsSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="rounded-lg border border-slate/20 p-4 space-y-3">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-24 rounded-full" />
            <Skeleton className="h-5 w-20 rounded-full" />
          </div>
          <Skeleton className="h-32 w-full" />
          <div className="flex gap-2">
            <Skeleton className="h-9 w-36" />
            <Skeleton className="h-9 w-24" />
          </div>
        </div>
      ))}
    </div>
  );
}

/** Originating tenant, always visible — this is a multi-tenant system and
 * the coach needs to know which mailbox a send will come from
 * (frontend/CLAUDE.md). */
function TenantPill({ tenantId }: { tenantId: TenantId }) {
  return <Pill>{tenantId === "tenant_a" ? "Tenant A" : "Tenant B"}</Pill>;
}
